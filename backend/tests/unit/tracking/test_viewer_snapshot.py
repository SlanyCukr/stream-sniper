"""Unit tests for the viewer-snapshot write path (Postgres-backed).

Mirrors the monkeypatch style of tests/unit/tracking/test_heartbeat.py: the gateway
tests patch the connection pool via a fake cursor context manager, and the
stream_monitor tests patch the gateway function by its import path in the
stream_monitor module.
"""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from stream_sniper.database import stream_viewer_sample_table_gateway as gateway
from stream_sniper.tracking import stream_monitor as monitor_module
from stream_sniper.tracking.stream_monitor import StreamMonitor, StreamStatus


def _streamer_data(ts_id=1, creator_id=2, twitch_username="somestreamer"):
    """Build a 15-element tracked_streamers row tuple matching _check_single_stream's unpack."""
    return (
        ts_id,               # 0 tracked_streamer_id
        creator_id,          # 1 creator_id
        twitch_username,     # 2 twitch_username
        "Some Streamer",     # 3 display_name
        True,                # 4 is_active
        None,                # 5 last_stream_check
        None,                # 6 last_processed_stream_id
        True,                # 7 processing_enabled
        None,                # 8 created_at
        None,                # 9 updated_at
        None,                # 10 created_by
        None,                # 11 notes
        "Some Streamer",     # 12 creator_display_name
        "http://example.com/avatar.jpg",  # 13 profile_image_url
        "admin",             # 14 created_by_username
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


def test_insert_stream_viewer_sample_db_success(monkeypatch):
    cursor = _FakeCursor()
    monkeypatch.setattr(gateway, "get_pool", lambda: _FakePool(cursor))

    result = gateway.insert_stream_viewer_sample_db(
        tracked_streamer_id=1,
        twitch_stream_session_id=555,
        sampled_at=datetime(2026, 7, 11, 12, 0, 0),
        viewer_count=42,
        title="Some Title",
        session_started_at=datetime(2026, 7, 11, 11, 0, 0),
    )

    assert result is True
    assert len(cursor.executed) == 1
    sql, params = cursor.executed[0]
    assert "INSERT INTO stream_sniper.stream_viewer_sample" in sql
    assert "ON CONFLICT" in sql
    assert "DO NOTHING" in sql
    assert params == (1, 555, datetime(2026, 7, 11, 12, 0, 0), 42, "Some Title", datetime(2026, 7, 11, 11, 0, 0))


def test_insert_stream_viewer_sample_db_returns_false_on_raise(monkeypatch):
    cursor = _FakeCursor(raise_on_execute=RuntimeError("boom"))
    monkeypatch.setattr(gateway, "get_pool", lambda: _FakePool(cursor))

    result = gateway.insert_stream_viewer_sample_db(
        tracked_streamer_id=1,
        twitch_stream_session_id=555,
        sampled_at=datetime(2026, 7, 11, 12, 0, 0),
        viewer_count=42,
        title="Some Title",
        session_started_at=None,
    )

    assert result is False


def test_select_session_viewer_samples_db_returns_rows(monkeypatch):
    rows = [(datetime(2026, 7, 11, 12, 0, 0), 42, "Some Title")]
    cursor = _FakeCursor(fetchall_result=rows)
    monkeypatch.setattr(gateway, "get_pool", lambda: _FakePool(cursor))

    result = gateway.select_session_viewer_samples_db(1, 555)

    assert result == rows
    sql, params = cursor.executed[0]
    assert "SELECT sampled_at, viewer_count, title" in sql
    assert "ORDER BY sampled_at ASC" in sql
    assert params == (1, 555)


def test_select_session_viewer_samples_db_returns_none_on_raise(monkeypatch):
    cursor = _FakeCursor(raise_on_execute=RuntimeError("boom"))
    monkeypatch.setattr(gateway, "get_pool", lambda: _FakePool(cursor))

    result = gateway.select_session_viewer_samples_db(1, 555)

    assert result is None


# ---------------------------------------------------------------------------
# stream_monitor write-site tests
# ---------------------------------------------------------------------------


@pytest.fixture
def monitor(monkeypatch):
    """A StreamMonitor with network/db side effects neutralized, except the piece under test."""
    monkeypatch.setattr(monitor_module, "TwitchAPI", lambda: object())
    m = StreamMonitor()
    monkeypatch.setattr(monitor_module, "update_stream_check_time_db", lambda *a, **kw: True)
    monkeypatch.setattr(monitor_module, "insert_stream_viewer_sample_db", lambda **kw: True)
    monkeypatch.setattr(monitor_module, "insert_stream_context_sample_db", lambda **kw: True)
    return m


@pytest.mark.asyncio
async def test_live_stream_records_viewer_snapshot(monitor, monkeypatch):
    calls = []

    def fake_insert(**kwargs):
        calls.append(kwargs)
        return True

    monkeypatch.setattr(monitor_module, "insert_stream_viewer_sample_db", fake_insert)

    status = StreamStatus(
        twitch_username="somestreamer",
        is_live=True,
        stream_id=999,
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
    monkeypatch.setattr(monitor_module, "insert_stream_context_sample_db", lambda **kw: calls.append(kw))
    status = StreamStatus(
        twitch_username="somestreamer", is_live=True, stream_id=999,
        title="New title", category_id="509658", category_name="Just Chatting",
        language="en", tags=["English", "NoBackseating"], is_mature=False,
    )
    monkeypatch.setattr(monitor, "_get_stream_status", AsyncMock(return_value=status))

    await monitor._check_single_stream(_streamer_data(ts_id=7))

    assert len(calls) == 1
    assert calls[0]["category_name"] == "Just Chatting"
    assert calls[0]["tags"] == ["English", "NoBackseating"]


@pytest.mark.asyncio
async def test_offline_stream_does_not_record_snapshot(monitor, monkeypatch):
    calls = []
    monkeypatch.setattr(monitor_module, "insert_stream_viewer_sample_db", lambda **kw: calls.append(kw))

    status = StreamStatus(twitch_username="somestreamer", is_live=False)
    monkeypatch.setattr(monitor, "_get_stream_status", AsyncMock(return_value=status))

    await monitor._check_single_stream(_streamer_data())

    assert calls == []


@pytest.mark.asyncio
async def test_gateway_returning_false_does_not_break_state_transition(monitor, monkeypatch):
    monkeypatch.setattr(monitor_module, "insert_stream_viewer_sample_db", lambda **kw: False)

    status = StreamStatus(
        twitch_username="somestreamer", is_live=True, stream_id=1, viewer_count=5,
    )
    monkeypatch.setattr(monitor, "_get_stream_status", AsyncMock(return_value=status))

    streamer_data = _streamer_data(twitch_username="somestreamer")
    await monitor._check_single_stream(streamer_data)

    # State-transition logic still ran despite the gateway reporting failure.
    assert monitor._last_stream_states["somestreamer"] is True


@pytest.mark.asyncio
async def test_gateway_raising_is_isolated_from_state_transition(monitor, monkeypatch):
    def raiser(**kw):
        raise RuntimeError("db exploded")

    monkeypatch.setattr(monitor_module, "insert_stream_viewer_sample_db", raiser)

    status = StreamStatus(
        twitch_username="somestreamer", is_live=True, stream_id=1, viewer_count=5,
    )
    monkeypatch.setattr(monitor, "_get_stream_status", AsyncMock(return_value=status))

    streamer_data = _streamer_data(twitch_username="somestreamer")
    # Must not raise out of _check_single_stream despite the gateway raising.
    await monitor._check_single_stream(streamer_data)

    assert monitor._last_stream_states["somestreamer"] is True
