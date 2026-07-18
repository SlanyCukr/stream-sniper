"""Unit tests for the tracking monitor's Discord "went live" alerts.

Mirrors the monkeypatch style of tests/unit/tracking/test_viewer_snapshot.py: the
Twitch client and DB gateways are neutralized at the stream_monitor module path, and
the Discord HTTP call (``deliver_discord``) is patched by its import name so no network
is touched. ``asyncio.to_thread`` still dispatches the patched callable in a worker
thread, exercising the real non-blocking seam.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest

from stream_sniper.application.tracking.models import TrackedStreamer
from stream_sniper.tracking import stream_monitor as monitor_module
from stream_sniper.tracking.status import StreamObservation
from stream_sniper.tracking.stream_monitor import StreamMonitor, StreamStatus

WEBHOOK = "https://discord.com/api/webhooks/abc/def"


def _streamer_data(ts_id=1, creator_id=2, twitch_username="somestreamer", display_name="Some Streamer"):
    now = datetime(2026, 7, 18, tzinfo=UTC)
    return TrackedStreamer(
        ts_id,
        creator_id,
        twitch_username,
        display_name,
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


def _live_status(session_id=999, **overrides):
    base = {
        "twitch_username": "somestreamer",
        "state": StreamObservation.LIVE,
        "twitch_stream_session_id": session_id,
        "title": "Live now",
        "viewer_count": 123,
        "category_name": "Just Chatting",
        "last_checked": datetime(2026, 7, 18, 12, 0, 0),
    }
    base.update(overrides)
    return StreamStatus(**base)


@pytest.fixture
def make_monitor(monkeypatch):
    """Factory for a StreamMonitor with network/DB side effects neutralized."""
    monkeypatch.setattr(monitor_module, "TwitchAPI", lambda: object())
    monkeypatch.setattr(monitor_module, "update_tracked_streamer_check_time_db", lambda *a, **kw: True)
    monkeypatch.setattr(monitor_module, "insert_live_snapshot_db", lambda **kw: True)

    def _make(webhook=WEBHOOK):
        return StreamMonitor(discord_webhook_url=webhook)

    return _make


def _patch_deliver(monkeypatch, side_effect=None):
    calls = []

    def fake_deliver(markdown, webhook_url):
        calls.append((markdown, webhook_url))
        if side_effect is not None:
            raise side_effect

    monkeypatch.setattr(monitor_module, "deliver_discord", fake_deliver)
    return calls


@pytest.mark.asyncio
async def test_alert_fires_on_offline_to_live(make_monitor, monkeypatch):
    monitor = make_monitor()
    monitor._last_stream_states["somestreamer"] = StreamObservation.OFFLINE
    calls = _patch_deliver(monkeypatch)
    monkeypatch.setattr(monitor, "_get_stream_status", AsyncMock(return_value=_live_status()))

    await monitor._check_single_stream(_streamer_data())

    assert len(calls) == 1
    markdown, url = calls[0]
    assert url == WEBHOOK
    assert markdown == (
        "🔴 **Some Streamer is live** — Live now\nJust Chatting · 123 viewers · https://twitch.tv/somestreamer"
    )
    assert 999 in monitor._alerted_sessions


@pytest.mark.asyncio
async def test_no_alert_when_webhook_unset(make_monitor, monkeypatch):
    monitor = make_monitor(webhook=None)
    monitor._last_stream_states["somestreamer"] = StreamObservation.OFFLINE
    calls = _patch_deliver(monkeypatch)
    monkeypatch.setattr(monitor, "_get_stream_status", AsyncMock(return_value=_live_status()))

    await monitor._check_single_stream(_streamer_data())

    assert calls == []


@pytest.mark.asyncio
async def test_first_observation_is_suppressed(make_monitor, monkeypatch):
    """A stream already live at the first poll (fresh state, e.g. after restart) is quiet."""
    monitor = make_monitor()
    calls = _patch_deliver(monkeypatch)
    monkeypatch.setattr(monitor, "_get_stream_status", AsyncMock(return_value=_live_status()))

    await monitor._check_single_stream(_streamer_data())

    assert calls == []
    # State is still committed so the next genuine transition can be observed.
    assert monitor._last_stream_states["somestreamer"] is StreamObservation.LIVE
    assert monitor._alerted_sessions == set()


@pytest.mark.asyncio
async def test_session_dedup_never_alerts_twice(make_monitor, monkeypatch):
    monitor = make_monitor()
    calls = _patch_deliver(monkeypatch)
    row = _streamer_data()
    status = _live_status(session_id=555)

    await monitor._maybe_alert_went_live(row, status, is_first_observation=False)
    await monitor._maybe_alert_went_live(row, status, is_first_observation=False)

    assert len(calls) == 1
    assert monitor._alerted_sessions == {555}


@pytest.mark.asyncio
async def test_alert_failure_is_swallowed(make_monitor, monkeypatch):
    monitor = make_monitor()
    monitor.logger = Mock()
    monitor._last_stream_states["somestreamer"] = StreamObservation.OFFLINE
    calls = _patch_deliver(monkeypatch, side_effect=RuntimeError("discord down"))
    monkeypatch.setattr(monitor, "_get_stream_status", AsyncMock(return_value=_live_status()))

    # Monitoring must not be affected by a failed alert.
    result = await monitor._check_single_stream(_streamer_data())

    assert result is StreamObservation.LIVE
    assert monitor._last_stream_states["somestreamer"] is StreamObservation.LIVE
    assert len(calls) == 1
    monitor.logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_ended_stream_forgets_alerted_session(make_monitor, monkeypatch):
    """Going offline prunes the streamer's session so the dedup set stays bounded."""
    monitor = make_monitor()
    monitor._alerted_sessions.add(999)
    monitor._streamer_session_ids["somestreamer"] = 999
    monitor._last_stream_states["somestreamer"] = StreamObservation.LIVE
    monkeypatch.setattr(
        monitor,
        "_get_stream_status",
        AsyncMock(return_value=StreamStatus(twitch_username="somestreamer", state=StreamObservation.OFFLINE)),
    )
    monkeypatch.setattr(monitor, "_queue_stream_for_processing", AsyncMock())

    await monitor._check_single_stream(_streamer_data())

    assert monitor._alerted_sessions == set()
    assert "somestreamer" not in monitor._streamer_session_ids


def test_format_live_alert_omits_missing_fields():
    row = _streamer_data(twitch_username="loginonly", display_name="Loginonly")
    status = StreamStatus(
        twitch_username="loginonly",
        state=StreamObservation.LIVE,
        twitch_stream_session_id=1,
        title=None,
        viewer_count=None,
        category_name=None,
    )

    assert StreamMonitor._format_live_alert(row, status) == (
        "🔴 **Loginonly is live**\nhttps://twitch.tv/loginonly"
    )
