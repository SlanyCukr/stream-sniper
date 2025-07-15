"""
Unit tests for database decorators.

Tests the database connection and cursor decorators that manage
database connections and error handling across the application.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import logging

from stream_sniper.database.decorators import with_cursor, with_cursor_connection, get_db_config


class TestDatabaseDecorators:
    """Test suite for database decorator functions."""

    def test_with_cursor_decorator_success(self):
        """Test successful execution with cursor decorator."""
        # Mock the pool and cursor
        mock_pool = Mock()
        mock_cursor = Mock()
        mock_connection_context = Mock()

        # Configure the mock
        mock_pool.get_cursor.return_value.__enter__.return_value = mock_cursor
        mock_pool.get_cursor.return_value.__exit__.return_value = None
        mock_cursor.fetchone.return_value = ("test_result",)

        # Create a test function with the decorator
        @with_cursor
        def test_function(test_arg, cursor):
            cursor.execute("SELECT * FROM test WHERE id = %s", (test_arg,))
            return cursor.fetchone()[0]

        # Patch get_pool to return our mock
        with patch("stream_sniper.database.decorators.get_pool", return_value=mock_pool):
            result = test_function("test_value")

        # Verify behavior
        assert result == "test_result"
        mock_pool.get_cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with("SELECT * FROM test WHERE id = %s", ("test_value",))

    def test_with_cursor_decorator_exception_handling(self):
        """Test exception handling in cursor decorator."""
        mock_pool = Mock()
        mock_cursor = Mock()

        # Configure cursor to raise exception
        mock_pool.get_cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Database error")

        @with_cursor
        def failing_function(cursor):
            cursor.execute("INVALID SQL")
            return "should not reach here"

        with patch("stream_sniper.database.decorators.get_pool", return_value=mock_pool):
            with pytest.raises(Exception) as exc_info:
                failing_function()

        assert "Database error" in str(exc_info.value)

    def test_with_cursor_decorator_logging(self, caplog):
        """Test that decorator logs errors appropriately."""
        mock_pool = Mock()
        mock_cursor = Mock()

        mock_pool.get_cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Test database error")

        @with_cursor
        def logging_test_function(cursor):
            cursor.execute("SELECT 1")

        with caplog.at_level(logging.ERROR):
            with patch("stream_sniper.database.decorators.get_pool", return_value=mock_pool):
                with pytest.raises(Exception):
                    logging_test_function()

        # Check that error was logged
        assert any("Database operation failed" in record.message for record in caplog.records)

    def test_with_cursor_connection_decorator_success(self):
        """Test successful execution with cursor connection decorator."""
        mock_pool = Mock()
        mock_connection = Mock()
        mock_cursor = Mock()

        # Configure the mocks
        mock_pool.get_connection.return_value.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.fetchone.return_value = (42,)

        @with_cursor_connection
        def test_function(test_data, cursor, connection):
            cursor.execute("INSERT INTO test (data) VALUES (%s) RETURNING id", (test_data,))
            connection.commit()
            return cursor.fetchone()[0]

        with patch("stream_sniper.database.decorators.get_pool", return_value=mock_pool):
            result = test_function("test_data")

        assert result == 42
        mock_connection.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once()
        mock_cursor.close.assert_called_once()

    def test_with_cursor_connection_decorator_exception(self):
        """Test exception handling in cursor connection decorator."""
        mock_pool = Mock()
        mock_connection = Mock()
        mock_cursor = Mock()

        mock_pool.get_connection.return_value.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Insert failed")

        @with_cursor_connection
        def failing_insert(data, cursor, connection):
            cursor.execute("INSERT INTO test (data) VALUES (%s)", (data,))
            connection.commit()

        with patch("stream_sniper.database.decorators.get_pool", return_value=mock_pool):
            with pytest.raises(Exception) as exc_info:
                failing_insert("test_data")

        assert "Insert failed" in str(exc_info.value)
        mock_cursor.close.assert_called_once()  # Should still close cursor

    def test_with_cursor_connection_cursor_cleanup(self):
        """Test that cursor is properly cleaned up even on exception."""
        mock_pool = Mock()
        mock_connection = Mock()
        mock_cursor = Mock()

        mock_pool.get_connection.return_value.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor
        mock_cursor.execute.side_effect = Exception("Cleanup test")

        @with_cursor_connection
        def cleanup_test(cursor, connection):
            cursor.execute("SELECT 1")

        with patch("stream_sniper.database.decorators.get_pool", return_value=mock_pool):
            with pytest.raises(Exception):
                cleanup_test()

        # Verify cursor was closed despite exception
        mock_cursor.close.assert_called_once()

    def test_with_cursor_connection_none_cursor_handling(self):
        """Test handling when cursor is None."""
        mock_pool = Mock()
        mock_connection = Mock()

        mock_pool.get_connection.return_value.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value = None  # Cursor is None

        @with_cursor_connection
        def none_cursor_test(cursor, connection):
            return "executed"

        with patch("stream_sniper.database.decorators.get_pool", return_value=mock_pool):
            result = none_cursor_test()

        assert result == "executed"
        # Should not call close on None cursor
        mock_connection.cursor.assert_called_once()

    def test_get_db_config_function(self):
        """Test get_db_config function returns pool configuration."""
        mock_pool = Mock()
        mock_config = {
            "host": "localhost",
            "database": "test_db",
            "user": "test_user",
            "password": "test_pass",
            "port": "5432",
        }
        mock_pool._config = mock_config

        with patch("stream_sniper.database.decorators.get_pool", return_value=mock_pool):
            config = get_db_config()

        assert config == mock_config

    def test_decorator_preserves_function_metadata(self):
        """Test that decorators preserve original function metadata."""

        @with_cursor
        def documented_function(arg1, cursor):
            """This function has documentation."""
            return arg1

        assert documented_function.__name__ == "documented_function"
        assert "This function has documentation" in documented_function.__doc__

        @with_cursor_connection
        def another_documented_function(arg1, cursor, connection):
            """Another documented function."""
            return arg1

        assert another_documented_function.__name__ == "another_documented_function"
        assert "Another documented function" in another_documented_function.__doc__

    def test_decorator_argument_passing(self):
        """Test that decorators correctly pass arguments to wrapped functions."""
        mock_pool = Mock()
        mock_cursor = Mock()
        mock_connection = Mock()

        # Test with_cursor argument passing
        mock_pool.get_cursor.return_value.__enter__.return_value = mock_cursor

        @with_cursor
        def multi_arg_function(arg1, arg2, keyword_arg=None, cursor=None):
            return (arg1, arg2, keyword_arg)

        with patch("stream_sniper.database.decorators.get_pool", return_value=mock_pool):
            result = multi_arg_function("value1", "value2", keyword_arg="keyword_value")

        assert result == ("value1", "value2", "keyword_value")

        # Test with_cursor_connection argument passing
        mock_pool.get_connection.return_value.__enter__.return_value = mock_connection
        mock_connection.cursor.return_value = mock_cursor

        @with_cursor_connection
        def multi_arg_function_with_conn(arg1, arg2, cursor=None, connection=None):
            return (arg1, arg2)

        with patch("stream_sniper.database.decorators.get_pool", return_value=mock_pool):
            result = multi_arg_function_with_conn("conn_value1", "conn_value2")

        assert result == ("conn_value1", "conn_value2")

    def test_decorator_return_value_handling(self):
        """Test that decorators properly handle different return values."""
        mock_pool = Mock()
        mock_cursor = Mock()

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

        with patch("stream_sniper.database.decorators.get_pool", return_value=mock_pool):
            assert none_return_function() is None
            assert tuple_return_function() == (1, 2, 3)
            assert dict_return_function() == {"key": "value"}

    def test_decorator_pool_acquisition_failure(self):
        """Test behavior when pool acquisition fails."""

        @with_cursor
        def pool_failure_test(cursor):
            return "should not reach here"

        with patch("stream_sniper.database.decorators.get_pool", side_effect=Exception("Pool unavailable")):
            with pytest.raises(Exception) as exc_info:
                pool_failure_test()

        assert "Pool unavailable" in str(exc_info.value)
