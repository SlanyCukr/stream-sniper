"""Chat metadata extraction, explicit row building, and insert-shape tests."""

from datetime import UTC, datetime
from unittest.mock import Mock

from stream_sniper.collector.archived.chat_parser import TwitchChatParser, extract_message_metadata
from stream_sniper.collector.archived.message_rows import build_message_rows
from stream_sniper.database.gateways.chat.message_table_gateway import insert_message_db


def _author(name: str | None, *, subscriber: bool = False, badges=None):
    return {
        "id": None,
        "name": name,
        "display_name": name,
        "badges": badges or [],
        "is_subscriber": subscriber,
    }


def test_extract_message_metadata_uses_normalized_fields():
    payload = {
        "author": _author(
            "viewer",
            subscriber=True,
            badges=[{"name": "subscriber", "version": "12"}],
        ),
        "emotes": [{"id": "25", "name": "Kappa"}],
    }

    assert extract_message_metadata(payload) == (True, "subscriber/12", 1, [("Kappa", "25")])


def test_build_message_rows_resolves_ids_mentions_and_metadata():
    batch = TwitchChatParser().parse_batch(
        [
            {
                "author": _author("viewer", subscriber=True),
                "message_id": "comment-123",
                "message": "hello @creator",
                "timestamp": 1_642_287_015_000_000,
                "emotes": [{"id": "25", "name": "Kappa"}],
            }
        ]
    )

    result = build_message_rows(
        batch,
        stream_id=10,
        chatter_ids={"viewer": 2, "creator": 1},
        message_ids={"hello @creator": 42},
    )

    assert result.message_count == 1
    assert result.emotes == (("Kappa", "25"),)
    assert result.rows == ((2, 1, 10, 42, datetime.fromtimestamp(1_642_287_015, UTC), True, None, 1, "comment-123"),)


def test_insert_message_db_persists_source_identity_conflict_safely():
    cursor = Mock()
    connection = Mock()
    items = [(1, None, 3, 4, datetime(2024, 1, 1), True, "moderator/1", 2, "comment-123")]

    insert_message_db(items, cursor, connection)

    sql, passed_items = cursor.executemany.call_args[0]
    assert sql.count("%s") == 9
    assert "ON CONFLICT (source_message_id)" in sql
    assert "WHERE source_message_id IS NOT NULL DO NOTHING" in sql
    assert passed_items == items
    connection.commit.assert_called_once_with()
