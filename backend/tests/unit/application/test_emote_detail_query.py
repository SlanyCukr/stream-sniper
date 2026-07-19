"""Contract tests for the single-emote drill-down application orchestration."""

from stream_sniper.application.scenes import emote_detail_query
from stream_sniper.application.scenes.emote_detail_query import get_emote_detail
from stream_sniper.database.gateways.analytics.emote_detail_gateway import (
    EmoteCreatorUsageRow,
    EmoteMetaRow,
    EmoteStreamUsageRow,
    EmoteTotalsRow,
    EmoteWeeklyUsageRow,
)


def _patch(monkeypatch, *, meta, totals=None, creators=None, weekly=None, streams=None) -> None:
    monkeypatch.setattr(emote_detail_query, "select_emote_meta_db", lambda _eid: meta)
    monkeypatch.setattr(
        emote_detail_query,
        "select_emote_totals_db",
        lambda _eid: totals if totals is not None else EmoteTotalsRow(0, 0, 0, 0, None),
    )
    monkeypatch.setattr(emote_detail_query, "select_emote_top_creators_db", lambda _eid, _limit: creators or [])
    monkeypatch.setattr(emote_detail_query, "select_emote_weekly_usage_db", lambda _eid, _weeks: weekly or [])
    monkeypatch.setattr(emote_detail_query, "select_emote_recent_streams_db", lambda _eid, _limit: streams or [])


def test_unknown_emote_returns_none(monkeypatch) -> None:
    _patch(monkeypatch, meta=None)
    assert get_emote_detail(999) is None


def test_dictionary_emote_with_no_usage_is_zero_not_none(monkeypatch) -> None:
    _patch(monkeypatch, meta=EmoteMetaRow(7, "agrPls", "bttv", "abc123", "2024-01-01T00:00:00"))

    result = get_emote_detail(7)

    assert result is not None
    assert result.meta.name == "agrPls"
    assert result.totals.usage == 0
    assert result.totals.last_used is None
    assert result.top_creators == []
    assert result.weekly_usage == []
    assert result.recent_streams == []


def test_assembles_all_sections(monkeypatch) -> None:
    _patch(
        monkeypatch,
        meta=EmoteMetaRow(7, "agrPls", "bttv", "abc123", "2024-01-01T00:00:00"),
        totals=EmoteTotalsRow(5000, 800, 42, 6, "2026-07-18T19:00:00"),
        creators=[
            EmoteCreatorUsageRow(1, "agraelus", "Agraelus", 4200, 700, 30),
            EmoteCreatorUsageRow(2, "claina", "Claina", 800, 100, 12),
        ],
        weekly=[EmoteWeeklyUsageRow("2026-07-06", 300), EmoteWeeklyUsageRow("2026-07-13", 450)],
        streams=[EmoteStreamUsageRow(99, "Finale", "2026-07-18T17:00:00", 1, "agraelus", "Agraelus", 150, 40)],
    )

    result = get_emote_detail(7)

    assert result is not None
    assert result.totals.usage == 5000
    assert result.totals.creator_count == 6
    assert [c.creator_id for c in result.top_creators] == [1, 2]
    assert result.top_creators[0].usage == 4200
    assert [w.week_start for w in result.weekly_usage] == ["2026-07-06", "2026-07-13"]
    assert result.recent_streams[0].stream_id == 99
    assert result.recent_streams[0].creator_display_name == "Agraelus"
