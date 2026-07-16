"""
Integration tests for API workflows.

Tests complete API workflows with real database interactions to ensure:
- End-to-end functionality
- Data flow between components
- API and database integration
"""

from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from stream_sniper.api.asgi import app
from tests.conftest import create_test_chatter, create_test_creator, create_test_message_text, create_test_stream


class TestAPIWorkflowIntegration:
    """Integration tests for complete API workflows."""

    @pytest.fixture
    def api_client_with_db(self, test_db_connection):
        """Create API client with real database connection."""
        # Mock the connection pool to use our test database
        with patch("stream_sniper.database.core.decorators.get_active_pool") as mock_get_pool:
            mock_pool = type("MockPool", (), {})()
            mock_pool.get_connection = lambda: test_db_connection
            mock_pool.get_cursor = lambda: test_db_connection.cursor()
            mock_pool.health_check = lambda: True
            mock_pool.get_pool_status = lambda: {"status": "active", "minconn": 2, "maxconn": 20}
            mock_get_pool.return_value = mock_pool

            with TestClient(app) as client:
                yield client

    def test_complete_stream_analytics_workflow(self, api_client_with_db, db_cursor):
        """Test complete workflow from data creation to API retrieval."""
        # Set up test data
        creator_data = {
            "nick": "api_test_streamer",
            "display_name": "API Test Streamer",
            "profile_image_url": "https://example.com/profile.jpg",
            "twitch_id": "987654321",
        }
        creator_id = create_test_creator(db_cursor, creator_data)

        stream_data = {
            "twitch_id": 123,
            "title": "API Integration Test Stream",
            "start_time": datetime(2024, 1, 15, 20, 0, 0),
            "end_time": datetime(2024, 1, 15, 23, 0, 0),
            "thumbnail_url": "https://example.com/thumb.jpg",
            "message_count": 0,
        }
        stream_id = create_test_stream(db_cursor, stream_data, creator_id)

        # Create chatters and messages
        chatters = ["api_viewer1", "api_viewer2", "api_viewer3"]
        messages = ["Hello API!", "Great integration test!", "@api_test_streamer awesome!"]

        chatter_ids = []
        message_text_ids = []

        for i, (chatter_nick, message_text) in enumerate(zip(chatters, messages)):
            chatter_id = create_test_chatter(db_cursor, chatter_nick)
            text_id = create_test_message_text(db_cursor, message_text)
            chatter_ids.append(chatter_id)
            message_text_ids.append(text_id)

            # Create message with tagging if it contains @
            tagged_chatter_id = None
            if "@" in message_text:
                # Find the tagged chatter (simplified - just use first chatter)
                tagged_chatter_id = chatter_ids[0]

            db_cursor.execute(
                """
                INSERT INTO message (chatter_id, stream_id, message_text_id, time, tagged_chatter_id)
                VALUES (%s, %s, %s, %s, %s)
            """,
                (chatter_id, stream_id, text_id, datetime.now(), tagged_chatter_id),
            )

        # Update stream message count
        db_cursor.execute("UPDATE stream SET message_count = %s WHERE id = %s", (len(messages), stream_id))

        # Test API endpoints

        # 1. Test GET /creators
        response = api_client_with_db.get("/creators")
        assert response.status_code == 200
        creators = response.json()
        assert len(creators) >= 1
        assert any(creator["display_name"] == creator_data["display_name"] for creator in creators)

        # 2. Test GET /streams/ for specific creator
        response = api_client_with_db.get(f"/streams/?creator_id={creator_id}&offset=0")
        assert response.status_code == 200
        data = response.json()
        assert "streams" in data
        assert "total" in data
        assert data["offset"] == 0
        assert data["limit"] == 20
        assert len(data["streams"]) >= 1

        # Find our test stream through the named public response contract.
        test_stream = None
        for stream in data["streams"]:
            if stream["stream_id"] == stream_id:
                test_stream = stream
                break

        assert test_stream is not None
        assert test_stream["creator_name"] == creator_data["display_name"]

        # 3. Test GET /stream/{stream_id}/ comprehensive analytics
        response = api_client_with_db.get(f"/streams/{stream_id}/")
        assert response.status_code == 200
        analytics = response.json()

        # Verify comprehensive stream info structure
        assert "info" in analytics
        assert "most_active_chatters" in analytics
        assert "most_tagged_chatters" in analytics
        assert "other_creators" in analytics
        assert "chatters" in analytics

        # Verify stream info
        info = analytics["info"]
        assert info["title"] == stream_data["title"]
        assert info["creator_nick"] == creator_data["nick"]
        assert info["creator_display_name"] == creator_data["display_name"]

        participants = analytics["chatters"]
        assert len(participants) == len(chatters)
        assert sorted(row["nick"] for row in participants) == sorted(chatters)

        # 4. Test GET /stream/{stream_id}/chatters
        response = api_client_with_db.get(f"/streams/{stream_id}/chatters")
        assert response.status_code == 200
        stream_chatters = response.json()
        assert len(stream_chatters) == len(chatters)

        # Verify all our test chatters are present
        chatter_nicks = [chatter["nick"] for chatter in stream_chatters]
        for nick in chatters:
            assert nick in chatter_nicks

        # 5. Test chatter-specific endpoints
        test_chatter_id = chatter_ids[0]
        test_chatter_nick = chatters[0]

        # Test GET /chatters/by-nick/{nick}
        response = api_client_with_db.get(f"/chatters/by-nick/{test_chatter_nick}")
        assert response.status_code == 200
        chatter_id_result = response.json()
        assert chatter_id_result["chatter_id"] == test_chatter_id

        # Test GET /chatter/{chatter_id}/messages/
        response = api_client_with_db.get(f"/chatters/{test_chatter_id}/messages/")
        assert response.status_code == 200
        chatter_messages = response.json()
        assert chatter_messages["total"] >= 1
        assert len(chatter_messages["messages"]) >= 1
        assert chatter_messages["messages"][0]["stream_id"] == stream_id
        assert chatter_messages["messages"][0]["text"] in messages

        # Test GET /stream/{stream_id}/chatter/{chatter_id}/messages
        response = api_client_with_db.get(f"/streams/{stream_id}/chatters/{test_chatter_id}/messages")
        assert response.status_code == 200
        stream_chatter_messages = response.json()
        assert len(stream_chatter_messages) >= 1
        assert stream_chatter_messages[0] in messages

    def test_api_pagination_workflow(self, api_client_with_db, db_cursor):
        """Test API pagination with multiple streams."""
        # Create creator and multiple streams
        creator_id = create_test_creator(
            db_cursor,
            {
                "nick": "pagination_creator",
                "display_name": "Pagination Creator",
                "profile_image_url": "url",
                "twitch_id": "111",
            },
        )

        # Create 5 streams
        stream_ids = []
        for i in range(5):
            stream_id = create_test_stream(
                db_cursor,
                {
                    "twitch_id": 2000 + i,
                    "title": f"Pagination Test Stream {i}",
                    "message_count": i * 10,
                },
                creator_id,
            )
            stream_ids.append(stream_id)

        # Test pagination
        # Get first page (offset 0)
        response = api_client_with_db.get(f"/streams/?creator_id={creator_id}&offset=0")
        assert response.status_code == 200
        page1 = response.json()

        # Get second page (offset 2)
        response = api_client_with_db.get(f"/streams/?creator_id={creator_id}&offset=2")
        assert response.status_code == 200
        page2 = response.json()

        # Verify pagination works
        assert "streams" in page1
        assert "streams" in page2
        assert "total" in page1
        assert "total" in page2

        # Should have fewer streams on second page
        assert len(page2["streams"]) <= len(page1["streams"])

        # Max offset should be consistent
        assert page1["total"] == page2["total"]

    def test_api_error_handling_workflow(self, api_client_with_db, db_cursor):
        """Test API error handling with non-existent resources."""
        # Test 404 errors

        # Non-existent stream
        response = api_client_with_db.get("/streams/99999/")
        assert response.status_code == 404
        assert "detail" in response.json()

        # Non-existent chatter — messages endpoint returns an empty page, not a 404
        response = api_client_with_db.get("/chatters/99999/messages/")
        assert response.status_code == 200
        assert response.json() == {"messages": [], "total": 0, "offset": 0, "limit": 50}

        # Non-existent chatter nick
        response = api_client_with_db.get("/chatters/by-nick/nonexistent_chatter")
        assert response.status_code == 404

        # Non-existent stream chatters
        response = api_client_with_db.get("/streams/99999/chatters")
        assert response.status_code == 404

        # Non-existent chatter messages in stream
        # First create valid stream and chatter for this test
        creator_id = create_test_creator(
            db_cursor,
            {
                "nick": "error_test_creator",
                "display_name": "Error Test",
                "profile_image_url": "url",
                "twitch_id": "222",
            },
        )
        stream_id = create_test_stream(db_cursor, creator_id=creator_id)
        chatter_id = create_test_chatter(db_cursor, "error_test_chatter")

        # Test valid stream with chatter that has no messages
        response = api_client_with_db.get(f"/streams/{stream_id}/chatters/{chatter_id}/messages")
        assert response.status_code == 404

    def test_api_data_consistency_workflow(self, api_client_with_db, db_cursor):
        """Test data consistency across different API endpoints."""
        # Create test data
        creator_id = create_test_creator(
            db_cursor,
            {
                "nick": "consistency_creator",
                "display_name": "Consistency Creator",
                "profile_image_url": "url",
                "twitch_id": "333",
            },
        )

        stream_id = create_test_stream(
            db_cursor,
            {"twitch_id": 3000, "title": "Consistency Test Stream", "message_count": 0},
            creator_id,
        )

        chatter_id = create_test_chatter(db_cursor, "consistency_chatter")
        text_id = create_test_message_text(db_cursor, "Consistency test message")

        # Create message
        db_cursor.execute(
            """
            INSERT INTO message (chatter_id, stream_id, message_text_id, time)
            VALUES (%s, %s, %s, %s)
        """,
            (chatter_id, stream_id, text_id, datetime.now()),
        )

        # Update stream message count
        db_cursor.execute("UPDATE stream SET message_count = 1 WHERE id = %s", (stream_id,))

        # Test consistency across endpoints

        # 1. Get stream info
        response = api_client_with_db.get(f"/streams/{stream_id}/")
        assert response.status_code == 200
        stream_analytics = response.json()

        # 2. Get stream chatters
        response = api_client_with_db.get(f"/streams/{stream_id}/chatters")
        assert response.status_code == 200
        stream_chatters = response.json()

        # 3. Get chatter messages
        response = api_client_with_db.get(f"/chatters/{chatter_id}/messages/")
        assert response.status_code == 200
        chatter_messages = response.json()

        # Verify consistency
        # Stream should show 1 unique chatter
        participants = stream_analytics["chatters"]
        assert len(participants) == 1

        # Stream chatters should include our test chatter
        chatter_found = False
        for chatter in stream_chatters:
            if chatter["chatter_id"] == chatter_id and chatter["nick"] == "consistency_chatter":
                chatter_found = True
                break
        assert chatter_found

        # Chatter should have messages
        assert chatter_messages["total"] >= 1
        assert chatter_messages["messages"][0]["text"] == "Consistency test message"

    def test_api_health_check_workflow(self, api_client_with_db):
        """Test health check endpoint with real database."""
        response = api_client_with_db.get("/health")
        assert response.status_code == 200

        health_data = response.json()
        assert "status" in health_data
        assert "database" in health_data
        assert "timestamp" in health_data
        assert "version" in health_data

        assert health_data["status"] == "healthy"
        assert health_data["database"]["healthy"] is True
        assert health_data["version"] == "1.0.0"

    def test_api_all_creators_workflow(self, api_client_with_db, db_cursor):
        """Test workflow with all creators parameter."""
        # Create multiple creators
        creator_ids = []
        for i in range(3):
            creator_id = create_test_creator(
                db_cursor,
                {
                    "nick": f"multi_creator_{i}",
                    "display_name": f"Multi Creator {i}",
                    "profile_image_url": f"url_{i}",
                    "twitch_id": 4000 + i,
                },
            )
            creator_ids.append(creator_id)

            # Create streams for each creator
            for j in range(2):
                create_test_stream(
                    db_cursor,
                    {
                        "twitch_id": 5000 + i * 10 + j,
                        "title": f"Stream {j} by Creator {i}",
                        "message_count": j * 5,
                    },
                    creator_id,
                )

        # Test getting streams for all creators
        response = api_client_with_db.get("/streams/?creator_id=-1&offset=0")
        assert response.status_code == 200

        data = response.json()
        assert "streams" in data
        assert "total" in data

        # Should have streams from all creators (6 total: 3 creators × 2 streams each)
        assert len(data["streams"]) >= 6

        # Test stream count for all creators
        assert data["total"] >= 6

    def test_api_unicode_handling_workflow(self, api_client_with_db, db_cursor):
        """Test API handling of unicode content."""
        # Create test data with unicode
        creator_id = create_test_creator(
            db_cursor,
            {
                "nick": "unicode_creator",
                "display_name": "Unicode Creator 🎮",
                "profile_image_url": "url",
                "twitch_id": "444",
            },
        )

        stream_id = create_test_stream(
            db_cursor,
            {"twitch_id": 6000, "title": "游戏直播 Gaming Stream 🎯", "message_count": 0},
            creator_id,
        )

        chatter_id = create_test_chatter(db_cursor, "unicode_chatter")
        text_id = create_test_message_text(db_cursor, "Hello! 😀🎮 你好世界 ★☆♦")

        # Create message
        db_cursor.execute(
            """
            INSERT INTO message (chatter_id, stream_id, message_text_id, time)
            VALUES (%s, %s, %s, %s)
        """,
            (chatter_id, stream_id, text_id, datetime.now()),
        )

        # Test API endpoints with unicode content

        # Test stream analytics
        response = api_client_with_db.get(f"/streams/{stream_id}/")
        assert response.status_code == 200
        analytics = response.json()

        # Verify unicode content is preserved
        info = analytics["info"]
        assert "游戏直播 Gaming Stream 🎯" in info["title"]
        assert "Unicode Creator 🎮" in info["creator_display_name"]

        # Test chatter messages
        response = api_client_with_db.get(f"/chatters/{chatter_id}/messages/")
        assert response.status_code == 200
        messages = response.json()

        # Verify unicode message content
        assert messages["total"] >= 1
        assert "Hello! 😀🎮 你好世界 ★☆♦" in messages["messages"][0]["text"]
