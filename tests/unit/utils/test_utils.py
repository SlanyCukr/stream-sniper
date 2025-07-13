"""
Unit tests for utility functions.

Tests datetime and time parsing utilities used throughout the application.
"""

import pytest
from datetime import datetime

from stream_sniper.utils.utils import (
    twitch_datetime_str_to_datetime,
    add_timedelta_to_point_in_time
)


class TestDateTimeUtils:
    """Test suite for datetime utility functions."""

    def test_twitch_datetime_str_to_datetime_success(self):
        """Test successful parsing of Twitch datetime string."""
        # Standard Twitch datetime format
        datetime_str = '2024-01-15T20:30:15Z'
        expected = datetime(2024, 1, 15, 20, 30, 15)
        
        result = twitch_datetime_str_to_datetime(datetime_str)
        
        assert result == expected
        assert isinstance(result, datetime)

    def test_twitch_datetime_str_to_datetime_different_times(self):
        """Test parsing different datetime strings."""
        test_cases = [
            ('2024-01-01T00:00:00Z', datetime(2024, 1, 1, 0, 0, 0)),
            ('2024-12-31T23:59:59Z', datetime(2024, 12, 31, 23, 59, 59)),
            ('2023-06-15T12:30:45Z', datetime(2023, 6, 15, 12, 30, 45))
        ]
        
        for datetime_str, expected in test_cases:
            result = twitch_datetime_str_to_datetime(datetime_str)
            assert result == expected

    def test_twitch_datetime_str_to_datetime_invalid_format(self):
        """Test behavior with invalid datetime format."""
        invalid_formats = [
            '2024-01-15 20:30:15',  # Missing T and Z
            '2024/01/15T20:30:15Z',  # Wrong date separator
            '2024-01-15T20:30:15',   # Missing Z
            'invalid-datetime',      # Completely invalid
            ''                      # Empty string
        ]
        
        for invalid_str in invalid_formats:
            with pytest.raises(ValueError):
                twitch_datetime_str_to_datetime(invalid_str)

    def test_add_timedelta_to_point_in_time_success(self):
        """Test successful addition of time delta to datetime."""
        base_time = datetime(2024, 1, 15, 20, 0, 0)
        
        # Test various time deltas
        test_cases = [
            ('1h', datetime(2024, 1, 15, 21, 0, 0)),      # 1 hour
            ('30m', datetime(2024, 1, 15, 20, 30, 0)),    # 30 minutes
            ('45s', datetime(2024, 1, 15, 20, 0, 45)),    # 45 seconds
            ('2h30m', datetime(2024, 1, 15, 22, 30, 0)),  # 2 hours 30 minutes
            ('1d', datetime(2024, 1, 16, 20, 0, 0)),      # 1 day
        ]
        
        for delta_str, expected in test_cases:
            result = add_timedelta_to_point_in_time(base_time, delta_str)
            assert result == expected

    def test_add_timedelta_to_point_in_time_zero_delta(self):
        """Test adding zero time delta."""
        base_time = datetime(2024, 1, 15, 20, 0, 0)
        
        result = add_timedelta_to_point_in_time(base_time, '0s')
        
        assert result == base_time

    def test_add_timedelta_to_point_in_time_complex_deltas(self):
        """Test complex time delta combinations."""
        base_time = datetime(2024, 1, 15, 20, 0, 0)
        
        test_cases = [
            ('1h30m45s', datetime(2024, 1, 15, 21, 30, 45)),
            ('2d12h30m', datetime(2024, 1, 18, 8, 30, 0)),
            ('1w', datetime(2024, 1, 22, 20, 0, 0)),  # 1 week
            ('1w2d3h4m5s', datetime(2024, 1, 24, 23, 4, 5))  # 1 week + 2 days + 3h4m5s
        ]
        
        for delta_str, expected in test_cases:
            result = add_timedelta_to_point_in_time(base_time, delta_str)
            assert result == expected

    def test_add_timedelta_to_point_in_time_invalid_delta(self):
        """Test behavior with invalid time delta strings."""
        base_time = datetime(2024, 1, 15, 20, 0, 0)
        
        invalid_deltas = [
            'invalid',      # Not a time format
            '1x',          # Invalid unit
            '',            # Empty string
            'abc123',      # Invalid format
        ]
        
        for invalid_delta in invalid_deltas:
            with pytest.raises((ValueError, TypeError)):
                add_timedelta_to_point_in_time(base_time, invalid_delta)

    def test_add_timedelta_to_point_in_time_edge_cases(self):
        """Test edge cases for time delta addition."""
        # Test with different base times
        base_times = [
            datetime(2024, 1, 1, 0, 0, 0),    # New year
            datetime(2024, 2, 29, 12, 0, 0),  # Leap year
            datetime(2024, 12, 31, 23, 59, 59), # End of year
        ]
        
        for base_time in base_times:
            result = add_timedelta_to_point_in_time(base_time, '1m')
            assert isinstance(result, datetime)
            assert result > base_time

    def test_datetime_utils_integration(self):
        """Test integration of both datetime utility functions."""
        # Parse a Twitch datetime string and add time delta
        twitch_str = '2024-01-15T20:00:00Z'
        parsed_datetime = twitch_datetime_str_to_datetime(twitch_str)
        
        # Add 3 hours 30 minutes (typical stream duration)
        stream_end = add_timedelta_to_point_in_time(parsed_datetime, '3h30m')
        
        expected_end = datetime(2024, 1, 15, 23, 30, 0)
        assert stream_end == expected_end

    def test_datetime_utils_type_safety(self):
        """Test that functions return correct types."""
        # Test twitch_datetime_str_to_datetime return type
        result1 = twitch_datetime_str_to_datetime('2024-01-15T20:00:00Z')
        assert isinstance(result1, datetime)
        
        # Test add_timedelta_to_point_in_time return type
        base_time = datetime.now()
        result2 = add_timedelta_to_point_in_time(base_time, '1h')
        assert isinstance(result2, datetime)

    def test_datetime_utils_immutability(self):
        """Test that original datetime objects are not modified."""
        original_time = datetime(2024, 1, 15, 20, 0, 0)
        original_copy = datetime(2024, 1, 15, 20, 0, 0)
        
        # Call function that should not modify original
        add_timedelta_to_point_in_time(original_time, '1h')
        
        # Verify original is unchanged
        assert original_time == original_copy

    def test_datetime_precision(self):
        """Test that datetime precision is maintained."""
        # Test with microseconds (though Twitch format doesn't include them)
        base_time = datetime(2024, 1, 15, 20, 30, 15, 123456)
        result = add_timedelta_to_point_in_time(base_time, '1s')
        
        expected = datetime(2024, 1, 15, 20, 30, 16, 123456)
        assert result == expected
        assert result.microsecond == 123456

    def test_timezone_handling(self):
        """Test that timezone information is handled correctly."""
        # Twitch uses UTC (Z suffix)
        datetime_str = '2024-01-15T20:30:15Z'
        result = twitch_datetime_str_to_datetime(datetime_str)
        
        # Result should be naive datetime (no timezone info)
        assert result.tzinfo is None
        
        # Should represent UTC time
        assert result == datetime(2024, 1, 15, 20, 30, 15)