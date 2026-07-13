from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

from stream_sniper.collector.live import live_message_sink as sink_module
from stream_sniper.collector.live.live_message_sink import LiveMessageSink, _emote_count


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
        user=SimpleNamespace(name="Viewer", subscriber=True, badges="subscriber/3"),
        text="hello @other",
        emotes=None,
        sent_timestamp=1_752_408_100_000,
    )


def test_emote_count_counts_each_range():
    assert _emote_count(None) == 0
    assert _emote_count("25:0-4,6-10/1902:12-16") == 3


@pytest.mark.asyncio
async def test_handle_maps_and_flushes_live_message(monkeypatch):
    written = []
    monkeypatch.setattr(sink_module, "ensure_live_stream_db", lambda *args: 77)
    monkeypatch.setattr(sink_module, "insert_new_chatter_db", lambda nick: 8)
    monkeypatch.setattr(sink_module, "find_or_insert_message_text_id_db", lambda text: 9)
    monkeypatch.setattr(sink_module, "bulk_insert_live_messages_db", lambda rows: written.extend(rows))
    sink = LiveMessageSink(buffer_size=10)

    assert await sink.handle(_message(), _stream()) is True
    await sink.flush()

    assert len(written) == 1
    row = written[0]
    assert row[0:4] == (8, None, 77, 9)
    assert row[5:9] == (True, "subscriber/3", 0, "uuid-1")
    assert sink.active_session("somestreamer") == 123


@pytest.mark.asyncio
async def test_flush_failure_retains_batch_for_retry(monkeypatch):
    attempts = 0

    def flaky(rows):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("database unavailable")

    monkeypatch.setattr(sink_module, "ensure_live_stream_db", lambda *args: 77)
    monkeypatch.setattr(sink_module, "insert_new_chatter_db", lambda nick: 8)
    monkeypatch.setattr(sink_module, "find_or_insert_message_text_id_db", lambda text: 9)
    monkeypatch.setattr(sink_module, "bulk_insert_live_messages_db", flaky)
    sink = LiveMessageSink(buffer_size=10)

    await sink.handle(_message(), _stream())
    await sink.flush()
    await sink.flush()

    assert attempts == 2
    assert sink._items == []


@pytest.mark.asyncio
async def test_finalize_flushes_and_marks_stream(monkeypatch):
    finalized = []
    monkeypatch.setattr(sink_module, "ensure_live_stream_db", lambda *args: 77)
    monkeypatch.setattr(sink_module, "finalize_live_stream_db", lambda *args: finalized.append(args))
    sink = LiveMessageSink()
    await sink.set_stream("somestreamer", _stream())

    assert await sink.finalize("somestreamer") == 77
    assert finalized == [(77, None)]
    assert sink.active_session("somestreamer") is None
