"""
Unit tests for database decorators.

Tests the database connection and cursor decorators that manage
database connections and error handling across the application.
"""

import logging
from inspect import signature
from unittest.mock import MagicMock, patch

import pytest

from stream_sniper.database.core.decorators import log_database_operation, with_cursor, with_cursor_connection


class TestDatabaseDecorators:
    """Test suite for database decorator functions."""

    def test_database_operation_success_has_no_formulaic_log_noise(self, caplog):
        @log_database_operation
        def operation():
            return 42

        with caplog.at_level(logging.DEBUG):
            assert operation() == 42

        assert caplog.records == []

    def test_with_cursor_decorator_success(self):
        """Test successful execution with cursor decorator."""
        # Mock the pool and cursor
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_connection_context = MagicMock()

        # Configure the mock
        mock_pool.get_cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool.get_cursor.return_value.__exit__.return_value = None
        mock_cursor.fetchone.return_value = ("test_result",)

        # Create a test function with the decorator
        @with_cursor
        def test_function(cursor, test_arg):
            cursor.execute("SELECT * FROM test WHERE id = %s", (test_arg,))
            return cursor.fetchone()[0]

        # Patch get_active_pool to return our mock
        with patch("stream_sniper.database.core.decorators.get_active_pool", return_value=mock_pool):
            result = test_function("test_value")

        # Verify behavior
        assert result == "test_result"
        mock_pool.get_cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with("SELECT * FROM test WHERE id = %s", ("test_value",))

    def test_with_cursor_decorator_exception_handling(self):
        """Test exception handling in cursor decorator."""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()

        # Configure cursor to raise exception
        mock_pool.get_cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Database error")

        @with_cursor
        def failing_function(cursor):
            cursor.execute("INVALID SQL")
            return "should not reach here"

        with patch("stream_sniper.database.core.decorators.get_active_pool", return_value=mock_pool):
            with pytest.raises(Exception) as exc_info:
                failing_function()

        assert "Database error" in str(exc_info.value)

    def test_with_cursor_propagates_without_duplicate_logging(self, caplog):
        mock_pool = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Test database error")

        @with_cursor
        def logging_test_function(cursor):
            cursor.execute("SELECT 1")

        with caplog.at_level(logging.ERROR):
            with patch("stream_sniper.database.core.decorators.get_active_pool", return_value=mock_pool):
                with pytest.raises(Exception):
                    logging_test_function()

        assert caplog.records == []

    def test_with_cursor_connection_decorator_success(self):
        """Test successful execution with cursor connection decorator."""
        mock_pool = MagicMock()
        mock_connection = MagicMock()
        mock_cursor = MagicMock()

        # Configure the mocks
        mock_pool.get_connection.return_value.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (42,)

        @with_cursor_connection
        def test_function(cursor, connection, test_data):
            cursor.execute("INSERT INTO test (data) VALUES (%s) RETURNING id", (test_data,))
            connection.commit()
            return cursor.fetchone()[0]

        with patch("stream_sniper.database.core.decorators.get_active_pool", return_value=mock_pool):
            result = test_function("test_data")

        assert result == 42
        mock_connection.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()

    def test_with_cursor_connection_decorator_exception(self):
        """Test exception handling in cursor connection decorator."""
        mock_pool = MagicMock()
        mock_connection = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection.return_value.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Insert failed")

        @with_cursor_connection
        def failing_insert(cursor, connection, data):
            cursor.execute("INSERT INTO test (data) VALUES (%s)", (data,))
            connection.commit()

        with patch("stream_sniper.database.core.decorators.get_active_pool", return_value=mock_pool):
            with pytest.raises(Exception) as exc_info:
                failing_insert("test_data")

        assert "Insert failed" in str(exc_info.value)
        mock_cursor.close.assert_called_once()  # Should still close cursor

    def test_with_cursor_connection_cursor_cleanup(self):
        """Test that cursor is properly cleaned up even on exception."""
        mock_pool = MagicMock()
        mock_connection = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_connection.return_value.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Cleanup test")

        @with_cursor_connection
        def cleanup_test(cursor, connection):
            cursor.execute("SELECT 1")

        with patch("stream_sniper.database.core.decorators.get_active_pool", return_value=mock_pool):
            with pytest.raises(Exception):
                cleanup_test()

        # Verify cursor was closed despite exception
        mock_cursor.close.assert_called_once()

    def test_with_cursor_connection_none_cursor_handling(self):
        """Test handling when cursor is None."""
        mock_pool = MagicMock()
        mock_connection = MagicMock()

        mock_pool.get_connection.return_value.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value = None  # Cursor is None

        @with_cursor_connection
        def none_cursor_test(cursor, connection):
            return "executed"

        with patch("stream_sniper.database.core.decorators.get_active_pool", return_value=mock_pool):
            result = none_cursor_test()

        assert result == "executed"
        # Should not call close on None cursor
        mock_connection.cursor.assert_called_once()

    def test_decorator_preserves_function_metadata(self):
        """Test that decorators preserve original function metadata."""

        @with_cursor
        def documented_function(cursor, arg1):
            """This function has documentation."""
            return arg1

        assert documented_function.__name__ == "documented_function"
        assert "This function has documentation" in documented_function.__doc__

        @with_cursor_connection
        def another_documented_function(cursor, connection, arg1):
            """Another documented function."""
            return arg1

        assert another_documented_function.__name__ == "another_documented_function"
        assert "Another documented function" in another_documented_function.__doc__

    def test_decorators_hide_injected_parameters_from_public_signatures(self):
        @with_cursor
        def read_row(cursor, row_id):
            return row_id

        @with_cursor_connection
        def write_row(cursor, connection, row_id):
            return row_id

        assert tuple(signature(read_row).parameters) == ("row_id",)
        assert tuple(signature(write_row).parameters) == ("row_id",)

    def test_decorator_argument_passing(self):
        """Test that decorators correctly pass arguments to wrapped functions."""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()
        mock_connection = MagicMock()

        # Test with_cursor argument passing
        mock_pool.get_cursor.return_value.__enter__.return_value = mock_cursor

        @with_cursor
        def multi_arg_function(cursor, arg1, arg2, keyword_arg=None):
            return (arg1, arg2, keyword_arg)

        with patch("stream_sniper.database.core.decorators.get_active_pool", return_value=mock_pool):
            result = multi_arg_function("value1", "value2", "keyword_value")

        assert result == ("value1", "value2", "keyword_value")

        # Test with_cursor_connection argument passing
        mock_pool.get_connection.return_value.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor

        @with_cursor_connection
        def multi_arg_function_with_conn(cursor, connection, arg1, arg2):
            return (arg1, arg2)

        with patch("stream_sniper.database.core.decorators.get_active_pool", return_value=mock_pool):
            result = multi_arg_function_with_conn("conn_value1", "conn_value2")

        assert result == ("conn_value1", "conn_value2")

    def test_decorator_return_value_handling(self):
        """Test that decorators properly handle different return values."""
        mock_pool = MagicMock()
        mock_cursor = MagicMock()

        mock_pool.get_cursor.return_value.__enter__.return_value = mock_cursor

        # Test returning None
        @with_cursor
        def none_return_function(cursor):
            return None

        # Test returning tuple
        @with_cursor
        def tuple_return_function(cursor):
            return (1, 2, 3)

        # Test returning dict
        @with_cursor
        def dict_return_function(cursor):
            return {"key": "value"}

        with patch("stream_sniper.database.core.decorators.get_active_pool", return_value=mock_pool):
            assert none_return_function() is None
            assert tuple_return_function() == (1, 2, 3)
            assert dict_return_function() == {"key": "value"}

    def test_decorator_pool_acquisition_failure(self):
        """Test behavior when pool acquisition fails."""

        @with_cursor
        def pool_failure_test(cursor):
            return "should not reach here"

        with patch("stream_sniper.database.core.decorators.get_active_pool", side_effect=Exception("Pool unavailable")):
            with pytest.raises(Exception) as exc_info:
                pool_failure_test()

        assert "Pool unavailable" in str(exc_info.value)
