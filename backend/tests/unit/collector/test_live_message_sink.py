import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from stream_sniper.collector.live import live_message_sink as sink_module
from stream_sniper.collector.live.live_message_sink import (
    LiveMessageFlushError,
    LiveMessageSink,
    _badge_text,
    _emote_count,
)


def _stream(session_id=123):
    return SimpleNamespace(
        id=str(session_id),
        started_at=datetime(2026, 7, 13, 12, 0, tzinfo=UTC),
        title="Live title",
        thumbnail_url="https://example.test/thumb.jpg",
    )


def _message(message_id="uuid-1"):
    return SimpleNamespace(
        id=message_id,
        room=SimpleNamespace(name="SomeStreamer"),
        user=SimpleNamespace(
            name="Viewer",
            subscriber=True,
            badges={"subscriber": "3", "moderator": "1"},
        ),
        text="hello @other",
        emotes=None,
        sent_timestamp=1_752_408_100_000,
    )


def test_emote_count_counts_each_range():
    assert _emote_count(None) == 0
    assert _emote_count("25:0-4,6-10/1902:12-16") == 3


def test_badge_text_handles_empty_and_already_serialized_values():
    assert _badge_text(None) is None
    assert _badge_text("subscriber/3") == "subscriber/3"


@pytest.mark.asyncio
async def test_handle_maps_and_flushes_live_message(monkeypatch):
    written = []
    monkeypatch.setattr(sink_module, "ensure_live_stream_db", lambda *args: 77)
    monkeypatch.setattr(sink_module, "find_or_insert_chatter_id_db", lambda nick: 8)
    monkeypatch.setattr(sink_module, "find_or_insert_message_text_id_db", lambda text: 9)
    monkeypatch.setattr(sink_module, "bulk_insert_live_messages_db", lambda rows: written.extend(rows))
    sink = LiveMessageSink(buffer_size=10)

    assert await sink.ingest_message(_message(), _stream()) is True
    await sink.flush()

    assert len(written) == 1
    row = written[0]
    assert row[0:4] == (8, None, 77, 9)
    assert row[5:9] == (True, "moderator/1,subscriber/3", 0, "uuid-1")
    assert sink.active_twitch_session_id("somestreamer") == 123


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("gateway", "message"),
    [
        ("find_or_insert_chatter_id_db", "Chatter persistence returned no ID"),
        ("find_or_insert_message_text_id_db", "Message-text persistence returned no ID"),
    ],
)
async def test_handle_rejects_missing_persistence_ids_before_caching(monkeypatch, gateway, message):
    monkeypatch.setattr(sink_module, "ensure_live_stream_db", lambda *args: 77)
    monkeypatch.setattr(sink_module, "find_or_insert_chatter_id_db", lambda nick: 8)
    monkeypatch.setattr(sink_module, "find_or_insert_message_text_id_db", lambda text: 9)
    monkeypatch.setattr(sink_module, gateway, lambda value: None)
    sink = LiveMessageSink(buffer_size=10)

    with pytest.raises(RuntimeError, match=message):
        await sink.ingest_message(_message(), _stream())

    assert sink._chatters.get("viewer") is not None if gateway != "find_or_insert_chatter_id_db" else not sink._chatters
    assert not sink._texts


@pytest.mark.asyncio
async def test_flush_failure_retains_batch_for_retry(monkeypatch):
    attempts = 0

    def flaky(rows):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("database unavailable")

    monkeypatch.setattr(sink_module, "ensure_live_stream_db", lambda *args: 77)
    monkeypatch.setattr(sink_module, "find_or_insert_chatter_id_db", lambda nick: 8)
    monkeypatch.setattr(sink_module, "find_or_insert_message_text_id_db", lambda text: 9)
    monkeypatch.setattr(sink_module, "bulk_insert_live_messages_db", flaky)
    sink = LiveMessageSink(buffer_size=10)

    await sink.ingest_message(_message(), _stream())
    with pytest.raises(LiveMessageFlushError, match="batch retained") as exc_info:
        await sink.flush()
    assert exc_info.value.retained_rows == 1
    assert len(sink._items) == 1

    assert await sink.flush() == 1

    assert attempts == 2
    assert sink._items == []


@pytest.mark.asyncio
async def test_finalize_failure_retains_stream_and_rows(monkeypatch):
    monkeypatch.setattr(sink_module, "ensure_live_stream_db", lambda *args: 77)
    monkeypatch.setattr(sink_module, "find_or_insert_chatter_id_db", lambda nick: 8)
    monkeypatch.setattr(sink_module, "find_or_insert_message_text_id_db", lambda text: 9)
    monkeypatch.setattr(
        sink_module,
        "bulk_insert_live_messages_db",
        lambda rows: (_ for _ in ()).throw(RuntimeError("database unavailable")),
    )
    sink = LiveMessageSink(buffer_size=10)
    await sink.ingest_message(_message(), _stream())

    with pytest.raises(LiveMessageFlushError):
        await sink.finalize("somestreamer")

    assert sink.active_twitch_session_id("somestreamer") == 123
    assert len(sink._items) == 1


@pytest.mark.asyncio
async def test_finalize_flushes_and_marks_stream(monkeypatch):
    finalized = []
    monkeypatch.setattr(sink_module, "ensure_live_stream_db", lambda *args: 77)
    monkeypatch.setattr(sink_module, "finalize_live_stream_db", lambda *args: finalized.append(args))
    sink = LiveMessageSink()
    await sink.ensure_stream("somestreamer", _stream())

    assert await sink.finalize("somestreamer") == 77
    assert finalized == [(77, None)]
    assert sink.active_twitch_session_id("somestreamer") is None


@pytest.mark.asyncio
async def test_finalize_serializes_terminal_flush_against_stale_messages(monkeypatch):
    written = []
    finalized = []
    monkeypatch.setattr(sink_module, "ensure_live_stream_db", lambda *args: 77)
    monkeypatch.setattr(sink_module, "find_or_insert_chatter_id_db", lambda nick: 8)
    monkeypatch.setattr(sink_module, "find_or_insert_message_text_id_db", lambda text: 9)
    monkeypatch.setattr(sink_module, "bulk_insert_live_messages_db", lambda rows: written.extend(rows))
    monkeypatch.setattr(sink_module, "finalize_live_stream_db", lambda *args: finalized.append(args))
    sink = LiveMessageSink(buffer_size=10)
    stream = _stream()
    assert await sink.ingest_message(_message("accepted"), stream) is True

    flush_started = asyncio.Event()
    release_flush = asyncio.Event()
    original_flush = sink.flush

    async def paused_flush():
        flush_started.set()
        await release_flush.wait()
        return await original_flush()

    sink.flush = paused_flush
    finalize_task = asyncio.create_task(sink.finalize("somestreamer"))
    await flush_started.wait()
    stale_ingest = asyncio.create_task(sink.ingest_message(_message("stale"), stream))
    await asyncio.sleep(0)
    assert stale_ingest.done() is False

    release_flush.set()
    assert await finalize_task == 77
    assert await stale_ingest is False

    assert [row[-1] for row in written] == ["accepted"]
    assert finalized == [(77, None)]
    assert sink._items == []
