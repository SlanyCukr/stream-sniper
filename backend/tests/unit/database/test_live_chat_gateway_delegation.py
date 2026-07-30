"""The live bulk writer must delegate to the shared ``message`` insert owner."""

from datetime import datetime
from unittest.mock import MagicMock

from stream_sniper.database.gateways.chat import live_chat_table_gateway


def _fake_pool_with(connection):
    pool = MagicMock()
    pool.get_connection.return_value.__enter__ = lambda self: connection
    pool.get_connection.return_value.__exit__ = lambda self, *exc: False
    return pool


def test_bulk_insert_delegates_to_shared_insert_message_db(monkeypatch):
    connection = MagicMock()
    cursor = connection.cursor.return_value
    monkeypatch.setattr(
        live_chat_table_gateway, "get_active_pool", lambda: _fake_pool_with(connection)
    )
    recorded = {}
    monkeypatch.setattr(
        live_chat_table_gateway,
        "insert_message_db",
        lambda items, cur, conn: recorded.update(items=list(items), cursor=cur, connection=conn),
    )

    row = (101, None, 10, 1001, datetime(2026, 7, 28, 18, 6), False, None, 1, "live-uuid-1")
    live_chat_table_gateway.bulk_insert_live_messages_db([row])

    assert recorded["items"] == [row]
    assert recorded["cursor"] is cursor
    assert recorded["connection"] is connection
    cursor.close.assert_called_once()


def test_bulk_insert_skips_pool_work_for_empty_batches(monkeypatch):
    def _fail():
        raise AssertionError("empty batch must not touch the pool")

    monkeypatch.setattr(live_chat_table_gateway, "get_active_pool", _fail)
    live_chat_table_gateway.bulk_insert_live_messages_db([])
