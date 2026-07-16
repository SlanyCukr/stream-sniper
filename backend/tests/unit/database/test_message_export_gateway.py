"""Unit tests for the streaming chat export gateway's resource ownership."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from stream_sniper.database.gateways.chat.message_export_gateway import iter_stream_message_export_db
from stream_sniper.database.gateways.chat.records import MessageReplayRow

_GATEWAY = "stream_sniper.database.gateways.chat.message_export_gateway"


def _pool_with_rows(rows):
    cursor = MagicMock()
    cursor.__iter__ = Mock(return_value=iter(rows))
    connection = MagicMock()
    connection.cursor.return_value = cursor
    pool = MagicMock()
    pool.get_connection.return_value.__enter__ = Mock(return_value=connection)
    pool.get_connection.return_value.__exit__ = Mock(return_value=False)
    return pool, connection, cursor


@patch(f"{_GATEWAY}.get_active_pool")
def test_streams_typed_rows_and_releases_resources(mock_get_pool):
    pool, connection, cursor = _pool_with_rows(
        [(1, "2026-07-01T18:00:00.000000", 11, "alice", "hello", True, "subscriber/12")]
    )
    mock_get_pool.return_value = pool

    assert list(iter_stream_message_export_db(7)) == [
        MessageReplayRow(1, "2026-07-01T18:00:00.000000", 11, "alice", "hello", True, "subscriber/12")
    ]
    assert connection.cursor.call_args.kwargs["name"].startswith("chat_export_7_")
    assert cursor.itersize == 5000
    assert cursor.execute.call_args.args[1] == (7,)
    cursor.close.assert_called_once()
    connection.rollback.assert_called_once()


@patch(f"{_GATEWAY}.get_active_pool")
def test_releases_resources_when_iteration_fails(mock_get_pool):
    pool, connection, cursor = _pool_with_rows([])
    cursor.__iter__ = Mock(side_effect=RuntimeError("database stream failed"))
    mock_get_pool.return_value = pool

    with pytest.raises(RuntimeError, match="database stream failed"):
        list(iter_stream_message_export_db(7))

    cursor.close.assert_called_once()
    connection.rollback.assert_called_once()
