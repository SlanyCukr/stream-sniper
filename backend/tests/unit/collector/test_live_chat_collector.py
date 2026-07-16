"""Lifecycle contract tests for the live chat collector."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from stream_sniper.collector.live import live_chat_collector as collector_module
from stream_sniper.collector.live.live_chat_collector import LiveChatCollector
from stream_sniper.collector.live.live_message_sink import LiveMessageFlushError


@pytest.mark.asyncio
async def test_collector_stop_retries_flush_before_closing_resources() -> None:
    collector = LiveChatCollector(channels=["somestreamer"])
    collector.sink.flush = AsyncMock(side_effect=[LiveMessageFlushError(3), 3])
    chat = MagicMock()
    twitch = SimpleNamespace(close=AsyncMock())
    collector.chat = chat
    collector.twitch = twitch

    await collector.stop()

    assert collector.sink.flush.await_count == 2
    chat.stop.assert_called_once_with()
    twitch.close.assert_awaited_once_with()

    await collector.stop()
    assert collector.chat is None
    assert collector.twitch is None


@pytest.mark.asyncio
async def test_collector_stop_can_retry_retained_rows_after_resources_close() -> None:
    collector = LiveChatCollector(channels=["somestreamer"])
    collector.sink.flush = AsyncMock(side_effect=[LiveMessageFlushError(3), LiveMessageFlushError(3), 3])
    chat = MagicMock()
    twitch = SimpleNamespace(close=AsyncMock())
    collector.chat = chat
    collector.twitch = twitch

    with pytest.raises(LiveMessageFlushError):
        await collector.stop()

    chat.stop.assert_called_once_with()
    twitch.close.assert_awaited_once_with()
    await collector.stop()
    assert collector.sink.flush.await_count == 3


def test_explicit_empty_channel_list_does_not_use_environment(monkeypatch) -> None:
    monkeypatch.setenv("LIVE_CHANNELS", "unexpected")

    collector = LiveChatCollector(channels=[])

    assert collector._static_channels == set()


@pytest.mark.asyncio
async def test_initialize_closes_partial_twitch_client(monkeypatch) -> None:
    monkeypatch.setenv("TWITCH_CLIENT_ID", "client")
    monkeypatch.setenv("TWITCH_CLIENT_SECRET", "secret")
    monkeypatch.setenv("TWITCH_BOT_REFRESH_TOKEN", "refresh")
    twitch = SimpleNamespace(
        set_user_authentication=AsyncMock(side_effect=RuntimeError("auth failed")),
        close=AsyncMock(),
    )
    monkeypatch.setattr(collector_module, "refresh_access_token", AsyncMock(return_value=("access", "refreshed")))
    monkeypatch.setattr(collector_module, "Twitch", AsyncMock(return_value=twitch))
    collector = LiveChatCollector(channels=["alice"])

    with pytest.raises(RuntimeError, match="auth failed"):
        await collector.initialize()

    twitch.close.assert_awaited_once_with()
    assert collector.twitch is None
    assert collector.chat is None


@pytest.mark.asyncio
async def test_start_surfaces_loop_failure_and_cancels_sibling(monkeypatch) -> None:
    collector = LiveChatCollector(channels=["alice"])
    collector.chat = MagicMock()
    collector._sync_channels = AsyncMock()
    sibling_cancelled = asyncio.Event()

    async def fail_flush() -> None:
        raise RuntimeError("flush failed")

    async def wait_for_status() -> None:
        try:
            await asyncio.Event().wait()
        finally:
            sibling_cancelled.set()

    monkeypatch.setattr(collector, "_flush_loop", fail_flush)
    monkeypatch.setattr(collector, "_status_loop", wait_for_status)

    with pytest.raises(RuntimeError, match="flush failed"):
        await collector.start()

    assert sibling_cancelled.is_set()


@pytest.mark.asyncio
async def test_sync_channels_reconciles_added_and_removed_rooms(monkeypatch) -> None:
    collector = LiveChatCollector(channels=["new"])
    collector.tracking_driven = False
    collector.channels = {"old"}
    collector.chat = SimpleNamespace(join_room=AsyncMock(), leave_room=AsyncMock())
    collector.sink.finalize = AsyncMock(return_value=None)
    monkeypatch.setattr(collector, "_ensure_creator", AsyncMock(return_value=True))

    await collector._sync_channels()

    collector.chat.join_room.assert_awaited_once_with(["new"])
    collector.chat.leave_room.assert_awaited_once_with(["old"])
    collector.sink.finalize.assert_awaited_once_with("old")
    assert collector.channels == {"new"}


@pytest.mark.asyncio
async def test_message_routing_fetches_then_caches_stream(monkeypatch) -> None:
    collector = LiveChatCollector(channels=["alice"])
    stream = SimpleNamespace(id="77")
    monkeypatch.setattr(collector, "_stream_for", AsyncMock(return_value=stream))
    collector.sink.ingest_message = AsyncMock()
    message = SimpleNamespace(room=SimpleNamespace(name="Alice"))

    await collector._on_message(message)
    await collector._on_message(message)

    collector._stream_for.assert_awaited_once_with("alice")
    assert collector.sink.ingest_message.await_count == 2


@pytest.mark.asyncio
async def test_reconcile_records_rollup_failure(monkeypatch) -> None:
    collector = LiveChatCollector(channels=["alice"])
    collector.channels = {"alice"}
    collector._sync_channels = AsyncMock()
    collector.sink.active_twitch_session_id = MagicMock(return_value=77)
    collector.sink.finalize = AsyncMock(return_value=12)
    monkeypatch.setattr(collector, "_stream_for", AsyncMock(return_value=None))
    monkeypatch.setattr(collector_module, "compute_stream_rollup", MagicMock(side_effect=RuntimeError("rollup failed")))

    await collector._reconcile_stream_sessions()

    assert collector.rollup_failures == {12: "rollup failed"}
    assert collector._pending_rollups == {12: 1}


@pytest.mark.asyncio
async def test_reconcile_retries_failed_rollup_on_next_status_cycle(monkeypatch) -> None:
    collector = LiveChatCollector(channels=["alice"])
    collector.channels = {"alice"}
    collector._sync_channels = AsyncMock()
    collector.sink.active_twitch_session_id = MagicMock(side_effect=[77, None])
    collector.sink.finalize = AsyncMock(return_value=12)
    monkeypatch.setattr(collector, "_stream_for", AsyncMock(return_value=None))
    successful_outcome = MagicMock()
    rollup = MagicMock(side_effect=[RuntimeError("rollup failed"), successful_outcome])
    monkeypatch.setattr(collector_module, "compute_stream_rollup", rollup)

    await collector._reconcile_stream_sessions()
    await collector._reconcile_stream_sessions()

    assert rollup.call_count == 2
    successful_outcome.require_success.assert_called_once_with()
    assert collector.rollup_failures == {}
    assert collector._pending_rollups == {}
