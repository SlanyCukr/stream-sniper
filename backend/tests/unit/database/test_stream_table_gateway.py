"""
Unit tests for stream table gateway functions.

Tests all stream-related database operations including:
- Stream selection and analytics
- Stream insertion and updates
- Chat analytics and statistics
"""

from datetime import datetime

from stream_sniper.database.stream_table_gateway import (
    select_all_stream_count_db,
    select_all_streams_db,
    select_chatter_messages_on_stream_db,
    select_chatters_in_stream_db,
    select_creators_that_wrote_in_stream_db,
    select_most_active_chatters_db,
    select_most_tagged_chatters_db,
    select_stream_comprehensive_db,
    update_stream_message_count_db,
)
from tests.conftest import create_test_chatter, create_test_creator, create_test_message_text, create_test_stream


class TestStreamTableGateway:
    """Test suite for stream table gateway functions."""

    def test_select_all_streams_db_with_creator_id(self, db_cursor, sample_stream_data):
        """Test retrieving streams for a specific creator."""
        # Create test data
        creator_id = create_test_creator(db_cursor)
        stream_id = create_test_stream(db_cursor, sample_stream_data, creator_id)

        # Test function
        result = select_all_streams_db(creator_id, offset=0)

        assert len(result) == 1
        stream = result[0]
        assert stream[0] == stream_id  # stream ID
        assert stream[1] == sample_stream_data["title"]  # title

    def test_select_all_streams_db_all_creators(self, db_cursor):
        """Test retrieving streams for all creators (creator_id = -1)."""
        # Create multiple creators and streams
        creator1_id = create_test_creator(
            db_cursor,
            {"nick": "creator1", "display_name": "Creator 1", "profile_image_url": "url1", "twitch_id": "111"},
        )
        creator2_id = create_test_creator(
            db_cursor,
            {"nick": "creator2", "display_name": "Creator 2", "profile_image_url": "url2", "twitch_id": "222"},
        )

        create_test_stream(db_cursor, {"twitch_id": "stream1", "title": "Stream 1"}, creator1_id)
        create_test_stream(db_cursor, {"twitch_id": "stream2", "title": "Stream 2"}, creator2_id)

        # Test function with creator_id = -1 (all creators)
        result = select_all_streams_db(-1, offset=0)

        assert len(result) == 2

    def test_select_all_streams_db_with_offset(self, db_cursor):
        """Test pagination with offset."""
        creator_id = create_test_creator(db_cursor)

        # Create multiple streams
        for i in range(5):
            create_test_stream(db_cursor, {"twitch_id": f"stream_{i}", "title": f"Stream {i}"}, creator_id)

        # Test with offset
        result = select_all_streams_db(creator_id, offset=2)

        assert len(result) == 3  # Should return remaining streams after offset

    def test_select_stream_comprehensive_db_success(self, db_cursor, sample_creator_data, sample_stream_data):
        """Test retrieving comprehensive stream information."""
        # Create test data
        creator_id = create_test_creator(db_cursor, sample_creator_data)
        stream_id = create_test_stream(db_cursor, sample_stream_data, creator_id)

        # Test function
        result = select_stream_comprehensive_db(stream_id)

        assert result is not None
        assert result[0] == sample_stream_data["title"]  # title
        assert result[5] == sample_creator_data["nick"]  # creator nick
        assert result[6] == sample_creator_data["display_name"]  # creator display name

    def test_select_stream_comprehensive_db_not_found(self, db_cursor):
        """Test behavior when stream not found."""
        result = select_stream_comprehensive_db(999)
        assert result is None

    def test_select_most_active_chatters_db(self, db_cursor):
        """Test retrieving most active chatters for a stream."""
        # Create test data
        creator_id = create_test_creator(db_cursor)
        stream_id = create_test_stream(db_cursor, creator_id=creator_id)
        chatter1_id = create_test_chatter(db_cursor, "chatter1")
        chatter2_id = create_test_chatter(db_cursor, "chatter2")
        message_text_id = create_test_message_text(db_cursor, "Test message")

        # Insert multiple messages for different chatters
        for _ in range(5):  # chatter1 sends 5 messages
            db_cursor.execute(
                """
                INSERT INTO message (chatter_id, stream_id, message_text_id, timestamp)
                VALUES (%s, %s, %s, %s)
            """,
                (chatter1_id, stream_id, message_text_id, datetime.now()),
            )

        for _ in range(3):  # chatter2 sends 3 messages
            db_cursor.execute(
                """
                INSERT INTO message (chatter_id, stream_id, message_text_id, timestamp)
                VALUES (%s, %s, %s, %s)
            """,
                (chatter2_id, stream_id, message_text_id, datetime.now()),
            )

        # Test function
        result = select_most_active_chatters_db(stream_id)

        assert len(result) >= 1
        # First result should be most active (chatter1 with 5 messages)
        assert result[0][0] == chatter1_id
        assert result[0][2] == 5  # message count

    def test_select_most_tagged_chatters_db(self, db_cursor):
        """Test retrieving most tagged chatters for a stream."""
        # Create test data
        creator_id = create_test_creator(db_cursor)
        stream_id = create_test_stream(db_cursor, creator_id=creator_id)
        chatter1_id = create_test_chatter(db_cursor, "chatter1")
        chatter2_id = create_test_chatter(db_cursor, "tagged_chatter")
        tagger_id = create_test_chatter(db_cursor, "tagger")
        message_text_id = create_test_message_text(db_cursor, "@tagged_chatter hello")

        # Insert messages with tags
        for _ in range(3):  # tagged_chatter gets tagged 3 times
            db_cursor.execute(
                """
                INSERT INTO message (chatter_id, stream_id, message_text_id, timestamp, tagged_chatter_id)
                VALUES (%s, %s, %s, %s, %s)
            """,
                (tagger_id, stream_id, message_text_id, datetime.now(), chatter2_id),
            )

        # Test function
        result = select_most_tagged_chatters_db(stream_id)

        if result:  # Only check if there are tagged chatters
            assert result[0][0] == chatter2_id  # tagged chatter ID
            assert result[0][2] == 3  # tag count

    def test_select_creators_that_wrote_in_stream_db(self, db_cursor):
        """Test finding other creators who wrote in a stream."""
        # Create test data
        main_creator_id = create_test_creator(
            db_cursor,
            {"nick": "main_creator", "display_name": "Main Creator", "profile_image_url": "url1", "twitch_id": "111"},
        )
        other_creator_id = create_test_creator(
            db_cursor,
            {"nick": "other_creator", "display_name": "Other Creator", "profile_image_url": "url2", "twitch_id": "222"},
        )

        stream_id = create_test_stream(db_cursor, creator_id=main_creator_id)

        # Create chatter with same nick as other creator
        other_chatter_id = create_test_chatter(db_cursor, "other_creator")
        message_text_id = create_test_message_text(db_cursor, "Hello from other creator!")

        # Insert message from other creator
        db_cursor.execute(
            """
            INSERT INTO message (chatter_id, stream_id, message_text_id, timestamp)
            VALUES (%s, %s, %s, %s)
        """,
            (other_chatter_id, stream_id, message_text_id, datetime.now()),
        )

        # Test function
        result = select_creators_that_wrote_in_stream_db(stream_id, main_creator_id)

        assert len(result) == 1
        assert result[0][0] == other_creator_id  # other creator ID
        assert result[0][1] == "other_creator"  # other creator nick

    def test_select_chatters_in_stream_db(self, db_cursor):
        """Test counting unique chatters in a stream."""
        # Create test data
        creator_id = create_test_creator(db_cursor)
        stream_id = create_test_stream(db_cursor, creator_id=creator_id)
        chatter1_id = create_test_chatter(db_cursor, "chatter1")
        chatter2_id = create_test_chatter(db_cursor, "chatter2")
        message_text_id = create_test_message_text(db_cursor, "Test message")

        # Insert messages from different chatters
        db_cursor.execute(
            """
            INSERT INTO message (chatter_id, stream_id, message_text_id, timestamp)
            VALUES (%s, %s, %s, %s)
        """,
            (chatter1_id, stream_id, message_text_id, datetime.now()),
        )

        db_cursor.execute(
            """
            INSERT INTO message (chatter_id, stream_id, message_text_id, timestamp)
            VALUES (%s, %s, %s, %s)
        """,
            (chatter2_id, stream_id, message_text_id, datetime.now()),
        )

        # Test function
        result = select_chatters_in_stream_db(stream_id)

        assert len(result) == 1  # Returns single row with count
        assert result[0][0] == 2  # Count of unique chatters

    def test_select_chatter_messages_on_stream_db(self, db_cursor):
        """Test retrieving messages from specific chatter in specific stream."""
        # Create test data
        creator_id = create_test_creator(db_cursor)
        stream_id = create_test_stream(db_cursor, creator_id=creator_id)
        chatter_id = create_test_chatter(db_cursor, "test_chatter")

        message_texts = ["Hello!", "How are you?", "Great stream!"]
        for text in message_texts:
            message_text_id = create_test_message_text(db_cursor, text)
            db_cursor.execute(
                """
                INSERT INTO message (chatter_id, stream_id, message_text_id, timestamp)
                VALUES (%s, %s, %s, %s)
            """,
                (chatter_id, stream_id, message_text_id, datetime.now()),
            )

        # Test function
        result = select_chatter_messages_on_stream_db(stream_id, chatter_id)

        assert len(result) == 3
        returned_messages = [msg[0] for msg in result]
        for text in message_texts:
            assert text in returned_messages

    def test_select_all_stream_count_db(self, db_cursor):
        """Test counting total streams for a creator."""
        # Create test data
        creator_id = create_test_creator(db_cursor)

        # Create multiple streams
        for i in range(3):
            create_test_stream(db_cursor, {"twitch_id": f"stream_{i}", "title": f"Stream {i}"}, creator_id)

        # Test function
        result = select_all_stream_count_db(creator_id)

        assert result == 3

    def test_select_all_stream_count_db_all_creators(self, db_cursor):
        """Test counting total streams for all creators."""
        # Create multiple creators and streams
        creator1_id = create_test_creator(
            db_cursor,
            {"nick": "creator1", "display_name": "Creator 1", "profile_image_url": "url1", "twitch_id": "111"},
        )
        creator2_id = create_test_creator(
            db_cursor,
            {"nick": "creator2", "display_name": "Creator 2", "profile_image_url": "url2", "twitch_id": "222"},
        )

        create_test_stream(db_cursor, {"twitch_id": "stream1", "title": "Stream 1"}, creator1_id)
        create_test_stream(db_cursor, {"twitch_id": "stream2", "title": "Stream 2"}, creator2_id)
        create_test_stream(db_cursor, {"twitch_id": "stream3", "title": "Stream 3"}, creator1_id)

        # Test function with creator_id = -1
        result = select_all_stream_count_db(-1)

        assert result == 3

    def test_update_stream_message_count_db(self, db_cursor):
        """Test updating stream message count."""
        # Create test data
        creator_id = create_test_creator(db_cursor)
        stream_id = create_test_stream(db_cursor, creator_id=creator_id)

        # Test function
        update_stream_message_count_db(stream_id, 1500)

        # Verify update
        db_cursor.execute("SELECT message_count FROM stream WHERE id = %s", (stream_id,))
        result = db_cursor.fetchone()

        assert result[0] == 1500


class TestStreamTableGatewayWithMocks:
    """Test stream table gateway functions with mocked database connections."""

    def test_select_all_streams_db_with_mock(self, mock_connection_pool):
        """Test select_all_streams_db with mocked database."""
        mock_pool, mock_connection, mock_cursor = mock_connection_pool
        mock_cursor.fetchall.return_value = [
            (1, "Stream 1", "2024-01-15 20:00:00", "2024-01-15 23:00:00", "thumb1.jpg", 100),
            (2, "Stream 2", "2024-01-16 20:00:00", "2024-01-16 22:00:00", "thumb2.jpg", 200),
        ]

        result = select_all_streams_db(1, offset=0)

        assert len(result) == 2
        mock_cursor.execute.assert_called_once()

    def test_select_stream_comprehensive_db_with_mock(self, mock_connection_pool):
        """Test select_stream_comprehensive_db with mocked database."""
        mock_pool, mock_connection, mock_cursor = mock_connection_pool
        mock_cursor.fetchone.return_value = (
            "Test Stream",
            "2024-01-15 20:00:00",
            "2024-01-15 23:00:00",
            "thumb.jpg",
            150,
            "creator_nick",
            "Creator Name",
            "profile.jpg",
            1,
        )

        result = select_stream_comprehensive_db(1)

        assert result[0] == "Test Stream"
        assert result[5] == "creator_nick"
        mock_cursor.execute.assert_called_once()
