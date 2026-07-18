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
async def test_start_sweeps_stale_sessions_before_loops(monkeypatch) -> None:
    # Zombie rows leaked by the previous downtime must be cleared on startup, before the
    # flush/status loops begin.
    collector = LiveChatCollector(channels=["alice"])
    collector.chat = MagicMock()
    collector._sync_channels = AsyncMock()
    sweep = AsyncMock()
    monkeypatch.setattr(collector, "_sweep_stale_sessions", sweep)

    async def fail_fast() -> None:
        raise RuntimeError("stop start()")

    monkeypatch.setattr(collector, "_flush_loop", fail_fast)
    monkeypatch.setattr(collector, "_status_loop", AsyncMock())

    with pytest.raises(RuntimeError, match="stop start"):
        await collector.start()

    sweep.assert_awaited_once_with()


def _stale(stream_id: int, session_id: int, nick: str):
    return SimpleNamespace(
        stream_id=stream_id,
        twitch_stream_session_id=session_id,
        creator_nick=nick,
    )


@pytest.mark.asyncio
async def test_sweep_finalizes_dead_candidates_and_enqueues_rollups(monkeypatch) -> None:
    collector = LiveChatCollector(channels=["alice"])
    monkeypatch.setattr(
        collector_module,
        "select_stale_live_sessions_db",
        MagicMock(return_value=[_stale(31, 901, "Alice"), _stale(32, 902, "bob")]),
    )
    finalize = MagicMock(return_value=True)
    monkeypatch.setattr(collector_module, "finalize_stale_live_session_db", finalize)
    monkeypatch.setattr(collector, "_stream_for", AsyncMock(return_value=None))  # not live on Twitch
    outcome = MagicMock()
    monkeypatch.setattr(collector_module, "compute_stream_rollup", MagicMock(return_value=outcome))

    await collector._sweep_stale_sessions()

    assert finalize.call_args_list == [((31,),), ((32,),)]
    # Channel lookups are lowercased before hitting Twitch/sink state.
    collector._stream_for.assert_any_await("alice")
    assert outcome.require_success.call_count == 2
    assert collector._pending_rollups == {}
    assert collector.rollup_failures == {}


@pytest.mark.asyncio
async def test_sweep_skips_session_active_in_sink(monkeypatch) -> None:
    # A session this collector is still capturing must never be swept, whatever the DB says.
    collector = LiveChatCollector(channels=["alice"])
    monkeypatch.setattr(
        collector_module, "select_stale_live_sessions_db", MagicMock(return_value=[_stale(31, 901, "alice")])
    )
    collector.sink.active_twitch_session_id = MagicMock(return_value=901)
    finalize = MagicMock()
    monkeypatch.setattr(collector_module, "finalize_stale_live_session_db", finalize)
    monkeypatch.setattr(collector, "_stream_for", AsyncMock())

    await collector._sweep_stale_sessions()

    finalize.assert_not_called()
    collector._stream_for.assert_not_awaited()


@pytest.mark.asyncio
async def test_sweep_skips_session_twitch_still_reports_live(monkeypatch) -> None:
    collector = LiveChatCollector(channels=["alice"])
    monkeypatch.setattr(
        collector_module, "select_stale_live_sessions_db", MagicMock(return_value=[_stale(31, 901, "alice")])
    )
    finalize = MagicMock()
    monkeypatch.setattr(collector_module, "finalize_stale_live_session_db", finalize)
    monkeypatch.setattr(collector, "_stream_for", AsyncMock(return_value=SimpleNamespace(id="901")))

    await collector._sweep_stale_sessions()

    finalize.assert_not_called()


@pytest.mark.asyncio
async def test_sweep_finalizes_when_channel_live_with_new_session(monkeypatch) -> None:
    # The streamer restarted: the channel is live again under a NEW session id, so the old
    # session is definitively dead and its row must be finalized.
    collector = LiveChatCollector(channels=["alice"])
    monkeypatch.setattr(
        collector_module, "select_stale_live_sessions_db", MagicMock(return_value=[_stale(31, 901, "alice")])
    )
    finalize = MagicMock(return_value=True)
    monkeypatch.setattr(collector_module, "finalize_stale_live_session_db", finalize)
    monkeypatch.setattr(collector, "_stream_for", AsyncMock(return_value=SimpleNamespace(id="777")))
    monkeypatch.setattr(collector_module, "compute_stream_rollup", MagicMock(return_value=MagicMock()))

    await collector._sweep_stale_sessions()

    finalize.assert_called_once_with(31)


@pytest.mark.asyncio
async def test_sweep_fails_closed_on_twitch_error(monkeypatch) -> None:
    # No definitive liveness answer -> keep the row open; a later sweep retries.
    collector = LiveChatCollector(channels=["alice"])
    monkeypatch.setattr(
        collector_module, "select_stale_live_sessions_db", MagicMock(return_value=[_stale(31, 901, "alice")])
    )
    finalize = MagicMock()
    monkeypatch.setattr(collector_module, "finalize_stale_live_session_db", finalize)
    monkeypatch.setattr(collector, "_stream_for", AsyncMock(side_effect=RuntimeError("twitch down")))

    await collector._sweep_stale_sessions()

    finalize.assert_not_called()


@pytest.mark.asyncio
async def test_sweep_lost_finalize_race_skips_rollup(monkeypatch) -> None:
    # finalize returns False when a concurrent real finalize already closed the row.
    collector = LiveChatCollector(channels=["alice"])
    monkeypatch.setattr(
        collector_module, "select_stale_live_sessions_db", MagicMock(return_value=[_stale(31, 901, "alice")])
    )
    monkeypatch.setattr(collector_module, "finalize_stale_live_session_db", MagicMock(return_value=False))
    monkeypatch.setattr(collector, "_stream_for", AsyncMock(return_value=None))
    rollup = MagicMock()
    monkeypatch.setattr(collector_module, "compute_stream_rollup", rollup)

    await collector._sweep_stale_sessions()

    rollup.assert_not_called()


@pytest.mark.asyncio
async def test_sweep_candidate_query_failure_is_swallowed(monkeypatch) -> None:
    # A broken sweep must never take down live capture.
    collector = LiveChatCollector(channels=["alice"])
    monkeypatch.setattr(
        collector_module, "select_stale_live_sessions_db", MagicMock(side_effect=RuntimeError("db down"))
    )
    rollup = MagicMock()
    monkeypatch.setattr(collector_module, "compute_stream_rollup", rollup)

    await collector._sweep_stale_sessions()

    rollup.assert_not_called()


@pytest.mark.asyncio
async def test_sweep_rollup_failure_lands_in_retry_queue(monkeypatch) -> None:
    # A swept stream whose rollup fails must enter the same retrying path finalized
    # streams use (retried by _retry_failed_rollups on later status cycles).
    collector = LiveChatCollector(channels=["alice"])
    monkeypatch.setattr(
        collector_module, "select_stale_live_sessions_db", MagicMock(return_value=[_stale(31, 901, "alice")])
    )
    monkeypatch.setattr(collector_module, "finalize_stale_live_session_db", MagicMock(return_value=True))
    monkeypatch.setattr(collector, "_stream_for", AsyncMock(return_value=None))
    monkeypatch.setattr(collector_module, "compute_stream_rollup", MagicMock(side_effect=RuntimeError("rollup failed")))

    await collector._sweep_stale_sessions()

    assert collector._pending_rollups == {31: 1}
    assert collector.rollup_failures == {31: "rollup failed"}


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
