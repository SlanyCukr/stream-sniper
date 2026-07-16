"""Checked rollup outcomes and transaction-preserving SQL phase tests."""

from unittest.mock import Mock

import pytest

from stream_sniper.analytics.rollups import rollup_engine
from stream_sniper.analytics.rollups.rollup_engine import RollupIncompleteError
from stream_sniper.database.gateways.analytics import (
    stream_chatter_stats_table_gateway as gateway,
)


def _install_successful_phases(monkeypatch, calls: list[str]) -> None:
    monkeypatch.setattr(
        rollup_engine,
        "ensure_emote_dictionary_seeded",
        lambda: calls.append("emote_seed"),
    )
    monkeypatch.setattr(
        rollup_engine,
        "recompute_stream_rollup_db",
        lambda _stream_id, _creator_id: calls.append("sql_rollup"),
    )
    monkeypatch.setattr(
        rollup_engine,
        "_compute_and_store_text_rollups",
        lambda _stream_id: calls.append("text_rollups"),
    )
    monkeypatch.setattr(
        rollup_engine,
        "_compute_and_store_copypasta_rollup",
        lambda _stream_id: calls.append("copypasta_rollup"),
    )
    monkeypatch.setattr(
        rollup_engine,
        "refresh_stream_events",
        lambda _stream_id: calls.append("scene_events"),
    )
    monkeypatch.setattr(
        rollup_engine.community,
        "recompute_creator_overlap",
        lambda *, blocking: calls.append(f"community_overlap:{blocking}") or True,
    )


def test_complete_rollup_returns_a_checked_success(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(rollup_engine, "select_stream_creator_id_db", lambda _stream_id: (7,))
    _install_successful_phases(monkeypatch, calls)

    outcome = rollup_engine.compute_stream_rollup(42)

    assert outcome.succeeded is True
    assert outcome.failures == ()
    assert outcome.completed_phases == (
        "emote_seed",
        "sql_rollup",
        "text_rollups",
        "copypasta_rollup",
        "scene_events",
        "community_overlap",
    )
    outcome.require_success()


def test_partial_rollup_records_failure_and_cannot_report_success(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(rollup_engine, "select_stream_creator_id_db", lambda _stream_id: (7,))
    _install_successful_phases(monkeypatch, calls)

    def fail_sql(_stream_id: int, _creator_id: int) -> None:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(rollup_engine, "recompute_stream_rollup_db", fail_sql)

    outcome = rollup_engine.compute_stream_rollup(42, refresh_overlap=False)

    assert outcome.succeeded is False
    assert [failure.phase for failure in outcome.failures] == ["sql_rollup"]
    assert "text_rollups" in outcome.completed_phases
    assert "community_overlap" not in outcome.completed_phases
    with pytest.raises(RollupIncompleteError, match="sql_rollup: database unavailable"):
        outcome.require_success()


def test_lock_skipped_overlap_is_not_reported_as_completed(monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr(rollup_engine, "select_stream_creator_id_db", lambda _stream_id: (7,))
    _install_successful_phases(monkeypatch, calls)
    monkeypatch.setattr(rollup_engine.community, "recompute_creator_overlap", lambda *, blocking: False)

    outcome = rollup_engine.compute_stream_rollup(42)

    assert "community_overlap" not in outcome.completed_phases
    assert outcome.failures == (
        rollup_engine.RollupPhaseFailure(
            phase="community_overlap",
            message="skipped because its lock was unavailable",
        ),
    )
    with pytest.raises(RollupIncompleteError, match="community_overlap: skipped because its lock was unavailable"):
        outcome.require_success()


@pytest.mark.parametrize(
    ("row", "reason"),
    [(None, "stream not found"), ((None,), "stream has no creator")],
)
def test_missing_rollup_target_is_an_explicit_skip(monkeypatch, row, reason):
    monkeypatch.setattr(rollup_engine, "select_stream_creator_id_db", lambda _stream_id: row)

    outcome = rollup_engine.compute_stream_rollup(42)

    assert outcome.succeeded is False
    assert outcome.skipped_reason == reason
    with pytest.raises(RollupIncompleteError, match=reason):
        outcome.require_success()


def test_sql_rollup_phases_share_one_cursor_and_commit(monkeypatch):
    calls: list[str] = []
    for name in (
        "_replace_time_buckets",
        "_replace_stream_chatter_stats",
        "_replace_stream_metrics",
        "_upsert_creator_chatter_stats",
        "_replace_stream_emote_stats",
    ):
        monkeypatch.setattr(
            gateway,
            name,
            lambda cursor, params, phase=name: calls.append(f"{phase}:{id(cursor)}:{params['sid']}:{params['cid']}"),
        )
    cursor = object()
    connection = Mock()

    gateway.recompute_stream_rollup_db.__wrapped__(cursor, connection, 42, 7)

    assert [call.split(":", 1)[0] for call in calls] == [
        "_replace_time_buckets",
        "_replace_stream_chatter_stats",
        "_replace_stream_metrics",
        "_upsert_creator_chatter_stats",
        "_replace_stream_emote_stats",
    ]
    assert {call.split(":")[1] for call in calls} == {str(id(cursor))}
    connection.commit.assert_called_once_with()


def test_sql_rollup_does_not_commit_after_a_phase_failure(monkeypatch):
    monkeypatch.setattr(gateway, "_replace_time_buckets", lambda _cursor, _params: None)

    def fail_phase(_cursor, _params) -> None:
        raise RuntimeError("phase failed")

    monkeypatch.setattr(gateway, "_replace_stream_chatter_stats", fail_phase)
    connection = Mock()

    with pytest.raises(RuntimeError, match="phase failed"):
        gateway.recompute_stream_rollup_db.__wrapped__(object(), connection, 42, 7)

    connection.commit.assert_not_called()
