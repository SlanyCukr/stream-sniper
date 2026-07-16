"""DatabaseBuffer durability contract tests."""

from contextlib import contextmanager
from unittest.mock import Mock

import pytest

from stream_sniper.collector.archived.database_buffer import DatabaseBuffer


def test_failed_flush_rolls_back_and_retains_pending_rows():
    connection = Mock()
    cursor = connection.cursor.return_value

    @contextmanager
    def connection_context():
        yield connection

    pool = Mock()
    pool.get_connection.side_effect = connection_context

    def fail_insert(_items, _cursor, _connection) -> None:
        raise RuntimeError("write failed")

    buffer = DatabaseBuffer.__new__(DatabaseBuffer)
    buffer.persist_batch = fail_insert
    buffer.buffer_len = 10
    buffer.items = [(1, "pending")]
    buffer.pool = pool

    with pytest.raises(RuntimeError, match="write failed"):
        buffer.flush()

    assert buffer.items == [(1, "pending")]
    connection.rollback.assert_called_once_with()
    connection.commit.assert_not_called()
    cursor.close.assert_called_once_with()
