"""PostgreSQL proof that archived-VOD retries do not duplicate committed messages."""

from datetime import datetime

import pytest

from stream_sniper.analytics.rollups.rollup_engine import RollupOutcome
from stream_sniper.collector.archived import vod_ingestion
from stream_sniper.collector.archived.twitch_vod_chat_downloader import VodChatStream
from stream_sniper.collector.archived.vod_ingestion import VodIngestionPipeline
from stream_sniper.database.gateways.chat.message_table_gateway import insert_message_db
from tests.conftest import create_test_creator

_MESSAGE_COUNT = 5_001


def _messages():
    for index in range(_MESSAGE_COUNT):
        yield {
            "message_id": f"vod-comment-{index}",
            "timestamp": 1_642_287_015_000_000 + index,
            "time_in_seconds": float(index),
            "author": {
                "id": "viewer-id",
                "name": "viewer",
                "display_name": "Viewer",
                "badges": [],
                "is_subscriber": False,
            },
            "message": "hello",
            "message_type": "text_message",
        }


def _vod() -> VodChatStream:
    return VodChatStream(
        messages=iter(_messages()),
        twitch_vod_id=987_654,
        started_at=datetime(2026, 7, 15, 20),
        title="Retry test",
        duration="1h",
        thumbnail_url="",
    )


def test_whole_vod_retry_is_idempotent_after_committed_buffer_flush(db_cursor, monkeypatch) -> None:
    creator_id = create_test_creator(db_cursor)
    db_cursor.connection.commit()
    calls = 0

    def fail_after_committed_prefix(items, cursor, connection):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("final flush failed")
        insert_message_db(items, cursor, connection)

    monkeypatch.setattr(vod_ingestion, "insert_message_db", fail_after_committed_prefix)
    monkeypatch.setattr(
        vod_ingestion,
        "compute_stream_rollup",
        lambda stream_id: RollupOutcome(stream_id=stream_id, completed_phases=("test",)),
    )

    with pytest.raises(RuntimeError, match="final flush failed"):
        VodIngestionPipeline(creator_id, "test_creator").ingest(_vod())

    db_cursor.execute("SELECT count(*) FROM message WHERE source_message_id LIKE 'vod-comment-%'")
    assert db_cursor.fetchone()[0] == 5_000

    monkeypatch.setattr(vod_ingestion, "insert_message_db", insert_message_db)
    result = VodIngestionPipeline(creator_id, "test_creator").ingest(_vod())

    db_cursor.execute(
        "SELECT count(*), count(DISTINCT source_message_id) "
        "FROM message WHERE stream_id = %s AND source_message_id LIKE 'vod-comment-%%'",
        (result.stream_id,),
    )
    assert db_cursor.fetchone() == (_MESSAGE_COUNT, _MESSAGE_COUNT)
    assert result.message_count == _MESSAGE_COUNT
