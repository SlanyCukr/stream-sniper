"""Unit tests for the viewer-snapshot write path (Postgres-backed).

Mirrors the monkeypatch style of tests/unit/tracking/test_heartbeat.py: the gateway
tests patch the connection pool via a fake cursor context manager, and the
stream_monitor tests patch the gateway function by its import path in the
stream_monitor module.
"""

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from stream_sniper.application.tracking.models import TrackedStreamer
from stream_sniper.collector.twitch_api import TwitchUpstreamError
from stream_sniper.database.core import decorators as db_decorators
from stream_sniper.database.gateways.streams import (
    stream_viewer_sample_table_gateway as gateway,
)
from stream_sniper.database.gateways.streams.records import StreamContextSample
from stream_sniper.tracking import stream_monitor as monitor_module
from stream_sniper.tracking.status import StreamObservation
from stream_sniper.tracking.stream_monitor import StreamMonitor, StreamStatus


def _streamer_data(ts_id=1, creator_id=2, twitch_username="somestreamer"):
    now = datetime(2026, 7, 11, tzinfo=UTC)
    return TrackedStreamer(
        ts_id,
        creator_id,
        twitch_username,
        "Some Streamer",
        True,
        None,
        None,
        True,
        now,
        now,
        1,
        None,
        "Some Streamer",
        "http://example.com/avatar.jpg",
        "admin",
    )


class _FakeCursor:
    """Minimal cursor stand-in supporting execute/fetchall and context-manager use."""

    def __init__(self, fetchall_result=None, raise_on_execute=None):
        self.executed = []
        self._fetchall_result = fetchall_result or []
        self._raise_on_execute = raise_on_execute

    def execute(self, sql, params=None):
        self.executed.append((sql, params))
        if self._raise_on_execute is not None:
            raise self._raise_on_execute

    def fetchall(self):
        return self._fetchall_result


class _FakeCursorCtx:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self._cursor

    def __exit__(self, *exc):
        return False


class _FakePool:
    def __init__(self, cursor):
        self._cursor = cursor

    def get_cursor(self, commit=False):
        return _FakeCursorCtx(self._cursor)


# ---------------------------------------------------------------------------
# Gateway tests
# ---------------------------------------------------------------------------


def test_insert_live_snapshot_uses_one_transaction_for_both_rows(monkeypatch):
    cursor = _FakeCursor()
    monkeypatch.setattr(db_decorators, "get_active_pool", lambda: _FakePool(cursor))
    sampled_at = datetime(2026, 7, 11, 12, 0, tzinfo=UTC)
    context = StreamContextSample(1, 555, sampled_at, None, "Title", "1", "Game", "en", ["tag"], False)

    assert gateway.insert_live_snapshot_db(1, 555, sampled_at, 42, "Title", None, context) is True

    assert len(cursor.executed) == 2
    assert "stream_viewer_sample" in cursor.executed[0][0]
    assert "stream_context_sample" in cursor.executed[1][0]


def test_insert_live_snapshot_propagates_operational_failure(monkeypatch):
    cursor = _FakeCursor(raise_on_execute=RuntimeError("boom"))
    monkeypatch.setattr(db_decorators, "get_active_pool", lambda: _FakePool(cursor))
    sampled_at = datetime(2026, 7, 11, 12, 0, tzinfo=UTC)
    context = StreamContextSample(1, 555, sampled_at, None, "Title", None, None, None, None, None)

    with pytest.raises(RuntimeError, match="boom"):
        gateway.insert_live_snapshot_db(1, 555, sampled_at, 42, "Title", None, context)


# ---------------------------------------------------------------------------
# stream_monitor write-site tests
# ---------------------------------------------------------------------------


@pytest.fixture
def monitor(monkeypatch):
    """A StreamMonitor with network/db side effects neutralized, except the piece under test."""
    monkeypatch.setattr(monitor_module, "TwitchAPI", lambda: object())
    m = StreamMonitor()
    monkeypatch.setattr(monitor_module, "update_tracked_streamer_check_time_db", lambda *a, **kw: True)
    monkeypatch.setattr(monitor_module, "insert_live_snapshot_db", lambda **kw: True)
    return m


@pytest.mark.asyncio
async def test_live_stream_records_viewer_snapshot(monitor, monkeypatch):
    calls = []

    def fake_insert(**kwargs):
        calls.append(kwargs)
        return True

    monkeypatch.setattr(monitor_module, "insert_live_snapshot_db", fake_insert)

    status = StreamStatus(
        twitch_username="somestreamer",
        state=StreamObservation.LIVE,
        twitch_stream_session_id=999,
        title="Live now",
        started_at=datetime(2026, 7, 11, 10, 0, 0),
        viewer_count=123,
        last_checked=datetime(2026, 7, 11, 12, 0, 0),
    )
    monkeypatch.setattr(monitor, "_get_stream_status", AsyncMock(return_value=status))

    streamer_data = _streamer_data(ts_id=7, creator_id=99)
    await monitor._check_single_stream(streamer_data)

    assert len(calls) == 1
    call = calls[0]
    assert call["tracked_streamer_id"] == streamer_data[0] == 7
    assert call["twitch_stream_session_id"] == 999
    assert call["viewer_count"] == 123
    assert call["title"] == "Live now"
    assert call["session_started_at"] == status.started_at


@pytest.mark.asyncio
async def test_live_stream_records_context_snapshot(monitor, monkeypatch):
    calls = []
    monkeypatch.setattr(
        monitor_module,
        "insert_live_snapshot_db",
        lambda **kwargs: calls.append(kwargs["context"]),
    )
    status = StreamStatus(
        twitch_username="somestreamer",
        state=StreamObservation.LIVE,
        twitch_stream_session_id=999,
        title="New title",
        category_id="509658",
        category_name="Just Chatting",
        language="en",
        tags=["English", "NoBackseating"],
        is_mature=False,
        viewer_count=123,
    )
    monkeypatch.setattr(monitor, "_get_stream_status", AsyncMock(return_value=status))

    await monitor._check_single_stream(_streamer_data(ts_id=7))

    assert len(calls) == 1
    assert calls[0].category_name == "Just Chatting"
    assert calls[0].tags == ["English", "NoBackseating"]


@pytest.mark.asyncio
async def test_offline_stream_does_not_record_snapshot(monitor, monkeypatch):
    calls = []
    monkeypatch.setattr(monitor_module, "insert_live_snapshot_db", lambda **kw: calls.append(kw))

    status = StreamStatus(twitch_username="somestreamer", state=StreamObservation.OFFLINE)
    monkeypatch.setattr(monitor, "_get_stream_status", AsyncMock(return_value=status))

    await monitor._check_single_stream(_streamer_data())

    assert calls == []


@pytest.mark.asyncio
async def test_gateway_returning_false_does_not_break_state_transition(monitor, monkeypatch):
    monkeypatch.setattr(monitor_module, "insert_live_snapshot_db", lambda **kw: False)

    status = StreamStatus(
        twitch_username="somestreamer",
        state=StreamObservation.LIVE,
        twitch_stream_session_id=1,
        viewer_count=5,
    )
    monkeypatch.setattr(monitor, "_get_stream_status", AsyncMock(return_value=status))

    streamer_data = _streamer_data(twitch_username="somestreamer")
    await monitor._check_single_stream(streamer_data)

    # State-transition logic still ran despite the gateway reporting failure.
    assert monitor._last_stream_states["somestreamer"] is StreamObservation.LIVE


@pytest.mark.asyncio
async def test_snapshot_failure_propagates_and_preserves_previous_state(monitor, monkeypatch):
    def raiser(**kw):
        raise RuntimeError("db exploded")

    monkeypatch.setattr(monitor_module, "insert_live_snapshot_db", raiser)

    status = StreamStatus(
        twitch_username="somestreamer",
        state=StreamObservation.LIVE,
        twitch_stream_session_id=1,
        viewer_count=5,
    )
    monkeypatch.setattr(monitor, "_get_stream_status", AsyncMock(return_value=status))

    streamer_data = _streamer_data(twitch_username="somestreamer")
    with pytest.raises(RuntimeError, match="db exploded"):
        await monitor._check_single_stream(streamer_data)

    assert "somestreamer" not in monitor._last_stream_states


@pytest.mark.asyncio
async def test_monitor_cycle_reports_failures_and_recovers(monitor, monkeypatch):
    streamers = [_streamer_data(ts_id=1), _streamer_data(ts_id=2, twitch_username="other")]
    monkeypatch.setattr(monitor_module, "select_active_tracked_streamers_db", lambda: streamers)
    monkeypatch.setattr(monitor_module.asyncio, "sleep", AsyncMock())
    monkeypatch.setattr(
        monitor,
        "_check_single_stream",
        AsyncMock(side_effect=[StreamObservation.LIVE, RuntimeError("snapshot failed")]),
    )

    await monitor._check_all_streams()

    degraded = monitor.get_monitoring_stats()
    assert degraded.successful_checks == 1
    assert degraded.failed_checks == 1
    assert degraded.unknown_checks == 0
    assert degraded.degraded is True
    assert degraded.last_successful_cycle is None

    monitor._check_single_stream = AsyncMock(side_effect=[StreamObservation.LIVE, StreamObservation.OFFLINE])
    await monitor._check_all_streams()

    recovered = monitor.get_monitoring_stats()
    assert recovered.successful_checks == 2
    assert recovered.failed_checks == 0
    assert recovered.degraded is False
    assert recovered.last_successful_cycle is not None


@pytest.mark.asyncio
async def test_only_twitch_transport_failures_become_unknown(monitor):
    monitor.twitch_api = SimpleNamespace(
        get_live_stream=AsyncMock(side_effect=TwitchUpstreamError("Twitch unavailable"))
    )

    unknown = await monitor._get_stream_status("somestreamer")
    assert unknown.state is StreamObservation.UNKNOWN

    monitor.twitch_api = SimpleNamespace(
        get_live_stream=AsyncMock(
            return_value=SimpleNamespace(
                id="not-an-integer",
                title="Broken",
                started_at=None,
                viewer_count=1,
                game_id="1",
                game_name="Game",
                language="en",
                tags=[],
                is_mature=False,
            )
        )
    )

    with pytest.raises(ValueError, match="invalid literal"):
        await monitor._get_stream_status("somestreamer")


@pytest.mark.asyncio
async def test_ended_stream_scheduling_failure_preserves_live_state_for_retry(monitor, monkeypatch):
    monitor._last_stream_states["somestreamer"] = StreamObservation.LIVE
    status = StreamStatus(twitch_username="somestreamer", state=StreamObservation.OFFLINE)
    monkeypatch.setattr(monitor, "_get_stream_status", AsyncMock(return_value=status))
    monkeypatch.setattr(
        monitor,
        "_get_recent_archived_videos",
        AsyncMock(side_effect=RuntimeError("Twitch archive unavailable")),
    )

    with pytest.raises(RuntimeError, match="archive unavailable"):
        await monitor._check_single_stream(_streamer_data(twitch_username="somestreamer"))

    assert monitor._last_stream_states["somestreamer"] is StreamObservation.LIVE
