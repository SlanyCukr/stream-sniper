"""Checked VOD ingestion pipeline tests."""

from datetime import datetime

from stream_sniper.analytics.rollups.rollup_engine import RollupOutcome
from stream_sniper.collector.archived import vod_ingestion
from stream_sniper.collector.archived.twitch_vod_chat_downloader import VodChatStream
from stream_sniper.collector.archived.vod_ingestion import VodIngestionPipeline


class FakeBuffer:
    def __init__(self, *_args) -> None:
        self.items: list[tuple] = []
        self.flushed = False

    def add_item(self, item: tuple) -> None:
        self.items.append(item)

    def flush(self) -> int:
        self.flushed = True
        return len(self.items)


def test_pipeline_returns_explicit_persisted_and_rollup_result(monkeypatch):
    buffer = FakeBuffer()
    emotes: list[list[tuple[str, str | None]]] = []
    counts: list[tuple[int, int]] = []
    monkeypatch.setattr(vod_ingestion, "DatabaseBuffer", lambda *_args: buffer)
    monkeypatch.setattr(vod_ingestion, "find_or_insert_chatter_id_db", lambda _nick: 1)
    monkeypatch.setattr(vod_ingestion, "insert_new_chatters_db", lambda _nicks: None)
    monkeypatch.setattr(vod_ingestion, "insert_message_texts_db", lambda _messages: None)
    monkeypatch.setattr(vod_ingestion, "select_all_chatters_db", lambda: {"viewer": 2})
    monkeypatch.setattr(vod_ingestion, "select_all_message_texts_db", lambda: {"hello": 3})
    monkeypatch.setattr(vod_ingestion, "upsert_twitch_emotes_db", lambda rows: emotes.append(rows))
    monkeypatch.setattr(vod_ingestion, "ensure_archived_stream_db", lambda *_args: 9)
    monkeypatch.setattr(
        vod_ingestion,
        "update_stream_message_count_db",
        lambda stream_id, count: counts.append((stream_id, count)),
    )
    outcome = RollupOutcome(stream_id=9, completed_phases=("sql_rollup",))
    monkeypatch.setattr(vod_ingestion, "compute_stream_rollup", lambda _stream_id: outcome)
    pipeline = VodIngestionPipeline(creator_id=7, creator_nick="creator")
    vod = VodChatStream(
        messages=iter(
            [
                {
                    "author": {
                        "id": None,
                        "name": "viewer",
                        "display_name": "viewer",
                        "badges": [],
                        "is_subscriber": False,
                    },
                    "message": "hello",
                    "timestamp": 1_642_287_015_000_000,
                    "emotes": [{"id": "25", "name": "Kappa"}],
                }
            ]
        ),
        twitch_vod_id=123,
        started_at=datetime(2024, 1, 15, 20),
        title="title",
        duration="1h",
        thumbnail_url="thumb",
    )

    result = pipeline.ingest(vod)

    assert result.twitch_vod_id == 123
    assert result.stream_id == 9
    assert result.message_count == 1
    assert result.batches[0].message_count == 1
    assert result.batches[0].emotes_discovered == (("Kappa", "25"),)
    assert result.rollup is outcome
    assert buffer.flushed is True
    assert len(buffer.items) == 1
    assert emotes == [[("Kappa", "25")]]
    assert counts == [(9, 1)]
