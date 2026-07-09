"""
Integration tests for database operations.

Tests the complete database workflow including:
- Database schema creation and management
- Cross-table relationships and constraints
- Data integrity and consistency
- Transaction handling
"""

from datetime import datetime

import psycopg2.errors
import pytest

from tests.conftest import create_test_chatter, create_test_creator, create_test_message_text, create_test_stream


class TestDatabaseIntegration:
    """Integration tests for complete database workflows."""

    def test_complete_stream_data_workflow(self, db_cursor):
        """Test complete workflow from creator to messages."""
        # 1. Create creator
        creator_data = {
            "nick": "test_streamer",
            "display_name": "Test Streamer",
            "profile_image_url": "https://example.com/profile.jpg",
            "twitch_id": "123456789",
        }
        creator_id = create_test_creator(db_cursor, creator_data)

        # 2. Create stream
        stream_data = {
            "twitch_id": "stream_abc123",
            "title": "Epic Gaming Session",
            "start_time": datetime(2024, 1, 15, 20, 0, 0),
            "end_time": datetime(2024, 1, 15, 23, 30, 0),
            "thumbnail_url": "https://example.com/thumbnail.jpg",
            "message_count": 0,
        }
        stream_id = create_test_stream(db_cursor, stream_data, creator_id)

        # 3. Create chatters
        chatters = ["viewer1", "viewer2", "viewer3"]
        chatter_ids = []
        for nick in chatters:
            chatter_id = create_test_chatter(db_cursor, nick)
            chatter_ids.append(chatter_id)

        # 4. Create message texts
        message_texts = ["Hello!", "Great stream!", "Thanks for the content!"]
        message_text_ids = []
        for text in message_texts:
            text_id = create_test_message_text(db_cursor, text)
            message_text_ids.append(text_id)

        # 5. Create messages linking everything together
        message_ids = []
        for i, (chatter_id, text_id) in enumerate(zip(chatter_ids, message_text_ids)):
            db_cursor.execute(
                """
                INSERT INTO message (chatter_id, stream_id, message_text_id, time)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """,
                (chatter_id, stream_id, text_id, datetime.now()),
            )
            message_id = db_cursor.fetchone()[0]
            message_ids.append(message_id)

        # 6. Update stream message count
        db_cursor.execute(
            """
            UPDATE stream SET message_count = %s WHERE id = %s
        """,
            (len(message_ids), stream_id),
        )

        # Verify complete data structure
        # Check creator exists
        db_cursor.execute("SELECT * FROM creator WHERE id = %s", (creator_id,))
        creator = db_cursor.fetchone()
        assert creator[1] == creator_data["nick"]

        # Check stream exists and links to creator
        db_cursor.execute("SELECT * FROM stream WHERE id = %s", (stream_id,))
        stream = db_cursor.fetchone()
        assert stream[1] == stream_data["twitch_id"]
        assert stream[7] == creator_id  # creator_id foreign key
        assert stream[6] == len(message_ids)  # message_count

        # Check all chatters exist
        db_cursor.execute("SELECT COUNT(*) FROM chatter WHERE id IN %s", (tuple(chatter_ids),))
        assert db_cursor.fetchone()[0] == len(chatters)

        # Check all message texts exist
        db_cursor.execute("SELECT COUNT(*) FROM message_text WHERE id IN %s", (tuple(message_text_ids),))
        assert db_cursor.fetchone()[0] == len(message_texts)

        # Check all messages exist with correct relationships
        db_cursor.execute(
            """
            SELECT m.id, c.nick, mt.text, s.title
            FROM message m
            JOIN chatter c ON m.chatter_id = c.id
            JOIN message_text mt ON m.message_text_id = mt.id
            JOIN stream s ON m.stream_id = s.id
            WHERE m.id IN %s
        """,
            (tuple(message_ids),),
        )

        messages = db_cursor.fetchall()
        assert len(messages) == len(message_ids)

        # Verify relationships
        for message in messages:
            message_id, chatter_nick, message_text, stream_title = message
            assert chatter_nick in chatters
            assert message_text in message_texts
            assert stream_title == stream_data["title"]

    def test_foreign_key_constraints(self, db_cursor):
        """Test that foreign key constraints are enforced."""
        # Try to create message with non-existent chatter
        with pytest.raises(Exception):  # Should raise foreign key constraint error
            db_cursor.execute(
                """
                INSERT INTO message (chatter_id, stream_id, message_text_id, time)
                VALUES (%s, %s, %s, %s)
            """,
                (999, 1, 1, datetime.now()),
            )

        # Try to create message with non-existent stream
        chatter_id = create_test_chatter(db_cursor, "test_chatter")
        with pytest.raises(Exception):  # Should raise foreign key constraint error
            db_cursor.execute(
                """
                INSERT INTO message (chatter_id, stream_id, message_text_id, time)
                VALUES (%s, %s, %s, %s)
            """,
                (chatter_id, 999, 1, datetime.now()),
            )

        # Try to create stream with non-existent creator
        with pytest.raises(Exception):  # Should raise foreign key constraint error
            db_cursor.execute(
                """
                INSERT INTO stream (twitch_id, title, creator_id)
                VALUES (%s, %s, %s)
            """,
                ("stream_123", "Test Stream", 999),
            )

    def test_unique_constraints(self, db_cursor):
        """Test that unique constraints are enforced."""
        # Test creator nick uniqueness
        creator_data = {
            "nick": "unique_creator",
            "display_name": "Unique Creator",
            "profile_image_url": "url",
            "twitch_id": "123",
        }
        create_test_creator(db_cursor, creator_data)

        # Try to create another creator with same nick
        with pytest.raises(Exception):  # Should raise unique constraint error
            create_test_creator(db_cursor, creator_data)

        # Test chatter nick uniqueness
        create_test_chatter(db_cursor, "unique_chatter")
        with pytest.raises(Exception):  # Should raise unique constraint error
            create_test_chatter(db_cursor, "unique_chatter")

        # Test message text uniqueness
        create_test_message_text(db_cursor, "unique_message")
        with pytest.raises(Exception):  # Should raise unique constraint error
            create_test_message_text(db_cursor, "unique_message")

    def test_cascade_behavior(self, db_cursor):
        """Test cascade behavior on deletions."""
        # Create complete data structure
        creator_id = create_test_creator(db_cursor)
        stream_id = create_test_stream(db_cursor, creator_id=creator_id)
        chatter_id = create_test_chatter(db_cursor, "test_chatter")
        text_id = create_test_message_text(db_cursor, "test_message")

        # Create message
        db_cursor.execute(
            """
            INSERT INTO message (chatter_id, stream_id, message_text_id, time)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """,
            (chatter_id, stream_id, text_id, datetime.now()),
        )
        message_id = db_cursor.fetchone()[0]

        # Verify message exists
        db_cursor.execute("SELECT COUNT(*) FROM message WHERE id = %s", (message_id,))
        assert db_cursor.fetchone()[0] == 1

        # Delete chatter — the schema declares plain FKs (no ON DELETE
        # CASCADE), so deleting a chatter still referenced by messages must
        # be rejected and the message must survive.
        with pytest.raises(psycopg2.errors.ForeignKeyViolation):
            db_cursor.execute("DELETE FROM chatter WHERE id = %s", (chatter_id,))

        db_cursor.execute("SELECT COUNT(*) FROM message WHERE id = %s", (message_id,))
        assert db_cursor.fetchone()[0] == 1

    def test_data_consistency_across_tables(self, db_cursor):
        """Test data consistency across related tables."""
        # Create data
        creator_id = create_test_creator(db_cursor)
        stream_id = create_test_stream(db_cursor, creator_id=creator_id)

        # Create multiple chatters and messages
        chatters_data = []
        for i in range(5):
            chatter_id = create_test_chatter(db_cursor, f"chatter_{i}")
            text_id = create_test_message_text(db_cursor, f"Message {i}")

            db_cursor.execute(
                """
                INSERT INTO message (chatter_id, stream_id, message_text_id, time)
                VALUES (%s, %s, %s, %s)
            """,
                (chatter_id, stream_id, text_id, datetime.now()),
            )

            chatters_data.append((chatter_id, text_id))

        # Verify consistency: all messages should reference existing entities
        db_cursor.execute(
            """
            SELECT COUNT(*) FROM message m
            WHERE m.chatter_id NOT IN (SELECT id FROM chatter)
               OR m.stream_id NOT IN (SELECT id FROM stream)
               OR m.message_text_id NOT IN (SELECT id FROM message_text)
        """
        )

        orphaned_messages = db_cursor.fetchone()[0]
        assert orphaned_messages == 0, "Found messages with invalid references"

    def test_transaction_rollback(self, test_db_connection):
        """Test transaction rollback behavior."""
        cursor = test_db_connection.cursor()
        cursor.execute("SET search_path TO stream_sniper")

        try:
            # Start transaction
            test_db_connection.autocommit = False

            # Create some data
            cursor.execute(
                """
                INSERT INTO creator (nick, display_name, profile_image_url, twitch_id)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """,
                ("rollback_test", "Rollback Test", "https://example.com/profile.jpg", "123"),
            )
            creator_id = cursor.fetchone()[0]

            # Verify data exists in transaction
            cursor.execute("SELECT COUNT(*) FROM creator WHERE id = %s", (creator_id,))
            assert cursor.fetchone()[0] == 1

            # Rollback transaction
            test_db_connection.rollback()

            # Verify data was rolled back
            cursor.execute("SELECT COUNT(*) FROM creator WHERE id = %s", (creator_id,))
            assert cursor.fetchone()[0] == 0

        finally:
            # Clear any (possibly aborted) transaction before restoring autocommit;
            # toggling autocommit inside an open transaction raises ProgrammingError
            # and would leave the shared session connection wedged for later tests.
            test_db_connection.rollback()
            test_db_connection.autocommit = True
            cursor.close()

    def test_concurrent_insert_handling(self, db_cursor):
        """Test handling of concurrent insert scenarios."""
        # Test scenario where same data might be inserted simultaneously
        creator_data = {
            "nick": "concurrent_creator",
            "display_name": "Concurrent Creator",
            "profile_image_url": "url",
            "twitch_id": "456",
        }

        # First insert should succeed
        creator_id_1 = create_test_creator(db_cursor, creator_data)

        # Second insert with same nick should fail due to unique constraint
        with pytest.raises(Exception):
            create_test_creator(db_cursor, creator_data)

        # Verify only one creator exists
        db_cursor.execute("SELECT COUNT(*) FROM creator WHERE nick = %s", (creator_data["nick"],))
        assert db_cursor.fetchone()[0] == 1

    def test_complex_query_performance(self, db_cursor):
        """Test performance of complex queries across multiple tables."""
        # Create substantial test data
        creator_id = create_test_creator(db_cursor)
        stream_ids = []

        # Create multiple streams
        for i in range(3):
            stream_id = create_test_stream(
                db_cursor, {"twitch_id": f"stream_{i}", "title": f"Stream {i}", "message_count": 0}, creator_id
            )
            stream_ids.append(stream_id)

        # Create chatters and messages
        chatter_ids = []
        for i in range(10):
            chatter_id = create_test_chatter(db_cursor, f"perf_chatter_{i}")
            chatter_ids.append(chatter_id)

        # Create messages across different streams
        for stream_id in stream_ids:
            for chatter_id in chatter_ids:
                text_id = create_test_message_text(db_cursor, f"Message from {chatter_id} in {stream_id}")
                db_cursor.execute(
                    """
                    INSERT INTO message (chatter_id, stream_id, message_text_id, time)
                    VALUES (%s, %s, %s, %s)
                """,
                    (chatter_id, stream_id, text_id, datetime.now()),
                )

        # Test complex aggregation query
        db_cursor.execute(
            """
            SELECT 
                s.title,
                COUNT(DISTINCT m.chatter_id) as unique_chatters,
                COUNT(m.id) as total_messages,
                c.display_name as creator_name
            FROM stream s
            JOIN creator c ON s.creator_id = c.id
            LEFT JOIN message m ON s.id = m.stream_id
            WHERE s.creator_id = %s
            GROUP BY s.id, s.title, c.display_name
            ORDER BY total_messages DESC
        """,
            (creator_id,),
        )

        results = db_cursor.fetchall()

        # Verify results
        assert len(results) == 3  # Should have 3 streams
        for result in results:
            stream_title, unique_chatters, total_messages, creator_name = result
            assert unique_chatters == 10  # Each stream should have 10 unique chatters
            assert total_messages == 10  # Each stream should have 10 messages
            assert "Stream" in stream_title

    def test_schema_constraints_validation(self, db_cursor):
        """Test that schema constraints are properly enforced."""
        # Test NOT NULL constraints
        with pytest.raises(Exception):
            db_cursor.execute("INSERT INTO creator (display_name) VALUES (%s)", ("No Nick",))

        with pytest.raises(Exception):
            db_cursor.execute("INSERT INTO chatter (display_name) VALUES (%s)", ("No Nick",))

        # Test data type constraints
        with pytest.raises(Exception):
            db_cursor.execute(
                """
                INSERT INTO stream (twitch_id, start_time, creator_id) 
                VALUES (%s, %s, %s)
            """,
                ("stream_123", "invalid_timestamp", 1),
            )

    def test_indexing_performance(self, db_cursor):
        """Test that database indexes are working effectively."""
        # Create substantial test data
        creator_id = create_test_creator(db_cursor)
        stream_id = create_test_stream(db_cursor, creator_id=creator_id)

        # Create many chatters and messages
        for i in range(100):
            chatter_id = create_test_chatter(db_cursor, f"idx_chatter_{i}")
            text_id = create_test_message_text(db_cursor, f"Index test message {i}")

            db_cursor.execute(
                """
                INSERT INTO message (chatter_id, stream_id, message_text_id, time)
                VALUES (%s, %s, %s, %s)
            """,
                (chatter_id, stream_id, text_id, datetime.now()),
            )

        # Test queries that should benefit from indexes
        # Query by creator nick (should use index if exists)
        db_cursor.execute("EXPLAIN SELECT * FROM creator WHERE nick = %s", ("test_creator",))

        # Query by chatter nick (should use index if exists)
        db_cursor.execute("EXPLAIN SELECT * FROM chatter WHERE nick = %s", ("idx_chatter_50",))

        # Query by message text (should use index if exists)
        db_cursor.execute("EXPLAIN SELECT * FROM message_text WHERE text = %s", ("Index test message 50",))

        # These tests mainly verify that the queries execute without error
        # In a real scenario, you'd analyze the EXPLAIN output for index usage
