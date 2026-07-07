"""
Unit tests for ChatProcessor class.

Tests chat message processing including:
- Nickname extraction from chat messages
- Message text extraction
- Chat processing workflow
"""

from unittest.mock import Mock

import pytest

from stream_sniper.collector.chat_processor import ChatProcessor


class TestChatProcessor:
    """Test suite for ChatProcessor class."""

    @pytest.fixture
    def mock_handler(self):
        """Mock message handler for testing."""
        return Mock()

    @pytest.fixture
    def chat_processor(self, mock_handler):
        """Create ChatProcessor instance with mock handler."""
        return ChatProcessor(creator_id=1, message_handling_fun=mock_handler)

    @pytest.fixture
    def sample_chat(self):
        """Sample chat messages for testing."""
        return [
            {
                "author": {"name": "viewer123"},
                "message": "Hello everyone!",
                "timestamp": 1642287015000000,  # Microseconds timestamp
            },
            {"author": {"name": "chatty_user"}, "message": "Great stream! @streamer", "timestamp": 1642287045000000},
            {"author": {"name": "stream_regular"}, "message": "PogChamp", "timestamp": 1642287075000000},
            {
                "author": {"name": "viewer123"},  # Duplicate user
                "message": "Thanks for the content!",
                "timestamp": 1642287105000000,
            },
        ]

    def test_get_nicks_success(self, chat_processor, sample_chat):
        """Test successful extraction of unique nicknames from chat."""
        nicks = chat_processor.get_nicks(sample_chat)

        # Should return unique nicknames only
        expected_nicks = {"viewer123", "chatty_user", "stream_regular"}
        assert set(nicks) == expected_nicks
        assert len(nicks) == 3

    def test_get_nicks_empty_chat(self, chat_processor):
        """Test nickname extraction from empty chat."""
        nicks = chat_processor.get_nicks([])

        assert nicks == []

    def test_get_nicks_single_message(self, chat_processor):
        """Test nickname extraction from single message."""
        single_message_chat = [{"author": {"name": "solo_viewer"}, "message": "First!", "timestamp": 1642287015000000}]

        nicks = chat_processor.get_nicks(single_message_chat)

        assert nicks == ["solo_viewer"]

    def test_get_nicks_duplicate_handling(self, chat_processor):
        """Test that duplicate nicknames are handled correctly."""
        duplicate_chat = [
            {"author": {"name": "user1"}, "message": "Message 1", "time_in_seconds": 1.0},
            {"author": {"name": "user2"}, "message": "Message 2", "time_in_seconds": 2.0},
            {"author": {"name": "user1"}, "message": "Message 3", "time_in_seconds": 3.0},
            {"author": {"name": "user1"}, "message": "Message 4", "time_in_seconds": 4.0},
        ]

        nicks = chat_processor.get_nicks(duplicate_chat)

        # Should only contain unique nicknames
        assert set(nicks) == {"user1", "user2"}
        assert len(nicks) == 2

    def test_get_messages_success(self, chat_processor, sample_chat):
        """Test successful extraction of unique messages from chat."""
        messages = chat_processor.get_messages(sample_chat)

        expected_messages = {"Hello everyone!", "Great stream! @streamer", "PogChamp", "Thanks for the content!"}

        assert set(messages) == expected_messages
        assert len(messages) == 4

    def test_get_messages_empty_chat(self, chat_processor):
        """Test message extraction from empty chat."""
        messages = chat_processor.get_messages([])

        assert messages == []

    def test_get_messages_duplicate_handling(self, chat_processor):
        """Test that duplicate messages are handled correctly."""
        duplicate_messages_chat = [
            {"author": {"name": "user1"}, "message": "Hello!", "time_in_seconds": 1.0},
            {"author": {"name": "user2"}, "message": "Hello!", "time_in_seconds": 2.0},  # Duplicate
            {"author": {"name": "user3"}, "message": "Goodbye!", "time_in_seconds": 3.0},
            {"author": {"name": "user4"}, "message": "Hello!", "time_in_seconds": 4.0},  # Another duplicate
        ]

        messages = chat_processor.get_messages(duplicate_messages_chat)

        # Should only contain unique messages
        assert set(messages) == {"Hello!", "Goodbye!"}
        assert len(messages) == 2

    def test_get_messages_empty_messages(self, chat_processor):
        """Test handling of empty message content."""
        empty_message_chat = [
            {"author": {"name": "user1"}, "message": "", "time_in_seconds": 1.0},
            {"author": {"name": "user2"}, "message": "Real message", "time_in_seconds": 2.0},
            {"author": {"name": "user3"}, "message": "", "time_in_seconds": 3.0},
        ]

        messages = chat_processor.get_messages(empty_message_chat)

        # Should include empty messages if they exist in the data
        assert "Real message" in messages
        # Check if empty messages are included when they exist in the data
        if "" in [msg["message"] for msg in empty_message_chat]:
            assert "" in messages

    def test_process_chat_success(self, chat_processor, mock_handler, sample_chat):
        """Test successful processing of entire chat."""
        stream_id = 123

        chat_processor.process_chat(sample_chat, stream_id)

        # Verify that handle_message was called for each message
        assert mock_handler.call_count == len(sample_chat)

        # Verify that each message was processed with correct parameters
        for i, call in enumerate(mock_handler.call_args_list):
            args, kwargs = call
            message_data, actual_stream_id = args

            assert actual_stream_id == stream_id
            assert message_data == sample_chat[i]

    def test_process_chat_empty(self, chat_processor, mock_handler):
        """Test processing empty chat."""
        stream_id = 123

        chat_processor.process_chat([], stream_id)

        # Handler should not be called for empty chat
        assert mock_handler.call_count == 0

    def test_process_chat_single_message(self, chat_processor, mock_handler):
        """Test processing chat with single message."""
        single_message = [
            {"author": {"name": "single_user"}, "message": "Only message", "time_in_seconds": 1642287015.0}
        ]
        stream_id = 456

        chat_processor.process_chat(single_message, stream_id)

        # Handler should be called once
        assert mock_handler.call_count == 1

        # Verify correct parameters
        args, kwargs = mock_handler.call_args
        message_data, actual_stream_id = args

        assert actual_stream_id == stream_id
        assert message_data == single_message[0]

    def test_creator_id_storage(self, mock_handler):
        """Test that creator_id is stored correctly."""
        creator_id = 999
        processor = ChatProcessor(creator_id=creator_id, message_handling_fun=mock_handler)

        assert processor.creator_id == creator_id

    def test_handle_message_function_storage(self, mock_handler):
        """Test that message_handling_fun function is stored correctly."""
        processor = ChatProcessor(creator_id=1, message_handling_fun=mock_handler)

        assert processor.message_handling_fun == mock_handler

    def test_chat_processor_with_malformed_messages(self, chat_processor, mock_handler):
        """Test handling of malformed chat messages."""
        malformed_chat = [
            # Missing author
            {"message": "Message without author", "time_in_seconds": 1.0},
            # Missing message
            {"author": {"name": "user_without_message"}, "time_in_seconds": 2.0},
            # Valid message
            {"author": {"name": "valid_user"}, "message": "Valid message", "time_in_seconds": 3.0},
        ]

        # Test get_nicks with malformed data
        try:
            nicks = chat_processor.get_nicks(malformed_chat)
            # Should handle missing author gracefully
            assert "valid_user" in nicks
        except (KeyError, AttributeError):
            # Expected behavior for malformed data
            pass

        # Test get_messages with malformed data
        try:
            messages = chat_processor.get_messages(malformed_chat)
            # Should handle missing message gracefully
            assert "Valid message" in messages
        except (KeyError, AttributeError):
            # Expected behavior for malformed data
            pass

    def test_chat_processor_performance_large_chat(self, chat_processor, mock_handler):
        """Test performance with large chat data."""
        # Create large chat data
        large_chat = []
        for i in range(1000):
            large_chat.append(
                {
                    "author": {"name": f"user_{i % 100}"},  # 100 unique users
                    "message": f"Message {i}",
                    "time_in_seconds": float(i),
                }
            )

        # Test nickname extraction
        nicks = chat_processor.get_nicks(large_chat)
        assert len(nicks) == 100  # Should have 100 unique users

        # Test message extraction
        messages = chat_processor.get_messages(large_chat)
        assert len(messages) == 1000  # Should have 1000 unique messages

        # Test processing
        chat_processor.process_chat(large_chat, 1)
        assert mock_handler.call_count == 1000

    def test_chat_processor_unicode_handling(self, chat_processor):
        """Test handling of unicode characters in messages."""
        unicode_chat = [
            {"author": {"name": "user_emoji"}, "message": "Hello! 😀🎮💜", "time_in_seconds": 1.0},
            {"author": {"name": "user_chinese"}, "message": "你好世界", "time_in_seconds": 2.0},
            {"author": {"name": "user_symbols"}, "message": "★☆♦♣♠♥", "time_in_seconds": 3.0},
        ]

        # Test nickname extraction with unicode
        nicks = chat_processor.get_nicks(unicode_chat)
        assert "user_emoji" in nicks
        assert "user_chinese" in nicks
        assert "user_symbols" in nicks

        # Test message extraction with unicode
        messages = chat_processor.get_messages(unicode_chat)
        assert "Hello! 😀🎮💜" in messages
        assert "你好世界" in messages
        assert "★☆♦♣♠♥" in messages
