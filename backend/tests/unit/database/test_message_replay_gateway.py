"""Unit tests for the message replay keyset gateway (select_stream_messages_db).

These are pure-SQL-shape tests: they mock the connection pool cursor and assert the
query text / bound params, so they do NOT need a live database.
"""

from stream_sniper.database.message_replay_gateway import select_stream_messages_db


class TestSelectStreamMessagesDb:
    def _captured_query(self, mock_cursor):
        assert mock_cursor.execute.call_count == 1
        return mock_cursor.execute.call_args[0][0]

    def test_time_projection_keeps_microsecond_precision(self, mock_connection_pool):
        """The replay cursor round-trips (m.time, m.id); the projected time MUST carry
        sub-second precision or a keyset boundary inside a dense second re-admits rows
        already returned (duplicate rows + non-advancing cursor)."""
        _mock_pool, _mock_connection, mock_cursor = mock_connection_pool

        select_stream_messages_db(7, 100)

        query = self._captured_query(mock_cursor)
        # microsecond format token, not the second-truncated 'HH24:MI:SS'
        assert "HH24:MI:SS.US" in query
        assert 'HH24:MI:SS\'' not in query.replace("HH24:MI:SS.US", "")

    def test_keyset_predicate_uses_time_and_id_tuple(self, mock_connection_pool):
        _mock_pool, _mock_connection, mock_cursor = mock_connection_pool

        select_stream_messages_db(7, 50, after_ts="2026-03-01T18:00:05.500000", after_id=102)

        query = self._captured_query(mock_cursor)
        params = mock_cursor.execute.call_args[0][1]
        assert "(m.time, m.id) > (%s::timestamp, %s)" in query
        assert "2026-03-01T18:00:05.500000" in params
        assert 102 in params

    def test_optional_filters_appended(self, mock_connection_pool):
        _mock_pool, _mock_connection, mock_cursor = mock_connection_pool

        select_stream_messages_db(7, 25, chatter_id=42, q="lol")

        query = self._captured_query(mock_cursor)
        params = mock_cursor.execute.call_args[0][1]
        assert "m.chatter_id = %s" in query
        assert "mt.text ILIKE %s" in query
        assert 42 in params
        assert "%lol%" in params
