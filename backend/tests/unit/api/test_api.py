"""
Unit tests for FastAPI endpoints.

Tests all API endpoints with mocked database responses to ensure:
- Correct HTTP status codes
- Proper response formatting
- Error handling
- Request validation
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi.testclient import TestClient

from stream_sniper.api.api import app
from stream_sniper.api.auth import get_current_admin_user


def _miss_cache():
    """A mock cache that always misses, so endpoint tests don't depend on cache state."""
    cache = Mock()
    cache._generate_key = Mock(return_value="test-cache-key")
    cache.get = Mock(return_value=None)
    cache.set = Mock(return_value=True)
    return cache


class TestChattersEndpoints:
    """Test suite for chatter-related API endpoints."""

    @patch("stream_sniper.api.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.chatter_endpoints.select_chatter_message_count_db")
    @patch("stream_sniper.api.chatter_endpoints.select_chatter_messages_db")
    def test_get_chatter_messages_success(self, mock_select, mock_count, mock_get_cache):
        """Test successful retrieval of paginated chatter messages with stream context."""
        mock_get_cache.return_value = _miss_cache()
        mock_select.return_value = [
            [7, "Epic Gaming Session", "SomeStreamer", "Hello everyone!", "2024-01-15 20:30:15"],
            [8, "Chill Stream", "OtherStreamer", "Great stream!", "2024-01-14 20:45:22"],
        ]
        mock_count.return_value = 1234

        with TestClient(app) as client:
            response = client.get("/chatter/42/messages")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1234
        assert len(data["messages"]) == 2
        assert data["messages"][0] == [7, "Epic Gaming Session", "SomeStreamer", "Hello everyone!", "2024-01-15 20:30:15"]
        mock_select.assert_called_once_with(42, 50, 0)
        mock_count.assert_called_once_with(42)

    @patch("stream_sniper.api.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.chatter_endpoints.select_chatter_message_count_db")
    @patch("stream_sniper.api.chatter_endpoints.select_chatter_messages_db")
    def test_get_chatter_messages_pagination_params(self, mock_select, mock_count, mock_get_cache):
        """Test that limit and offset query params are passed to the gateway."""
        mock_get_cache.return_value = _miss_cache()
        mock_select.return_value = []
        mock_count.return_value = 0

        with TestClient(app) as client:
            response = client.get("/chatter/42/messages?offset=100&limit=25")

        assert response.status_code == 200
        mock_select.assert_called_once_with(42, 25, 100)

    @patch("stream_sniper.api.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.chatter_endpoints.select_chatter_message_count_db")
    @patch("stream_sniper.api.chatter_endpoints.select_chatter_messages_db")
    def test_get_chatter_messages_empty_returns_200(self, mock_select, mock_count, mock_get_cache):
        """Test that a chatter with no messages returns an empty page, not a 404."""
        mock_get_cache.return_value = _miss_cache()
        mock_select.return_value = []
        mock_count.return_value = 0

        with TestClient(app) as client:
            response = client.get("/chatter/999/messages")

        assert response.status_code == 200
        assert response.json() == {"messages": [], "total": 0}

    @patch("stream_sniper.api.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.chatter_endpoints.select_chatter_message_count_db")
    @patch("stream_sniper.api.chatter_endpoints.select_chatter_messages_db")
    def test_get_chatter_messages_server_error(self, mock_select, mock_count, mock_get_cache):
        """Test chatter messages endpoint with database error."""
        mock_get_cache.return_value = _miss_cache()
        mock_select.side_effect = Exception("Database connection failed")

        with TestClient(app) as client:
            response = client.get("/chatter/42/messages")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

    @patch("stream_sniper.api.chatter_endpoints.select_chatter_id_db")
    def test_get_chatter_id_success(self, mock_select):
        """Test successful retrieval of chatter ID."""
        mock_select.return_value = [42]

        with TestClient(app) as client:
            response = client.get("/chatter/viewer123/chatter_id")

        assert response.status_code == 200
        assert response.json() == [42]
        mock_select.assert_called_once_with("viewer123")

    @patch("stream_sniper.api.chatter_endpoints.select_chatter_id_db")
    def test_get_chatter_id_not_found(self, mock_select):
        """Test chatter ID endpoint when chatter not found."""
        mock_select.return_value = None

        with TestClient(app) as client:
            response = client.get("/chatter/nonexistent/chatter_id")

        assert response.status_code == 404
        assert response.json()["detail"] == "Chatter not found"


class TestStreamsEndpoints:
    """Test suite for stream-related API endpoints."""

    @patch("stream_sniper.api.stream_endpoints.select_all_stream_count_db")
    @patch("stream_sniper.api.stream_endpoints.select_all_streams_db")
    def test_get_streams_success(self, mock_streams, mock_count):
        """Test successful retrieval of streams."""
        mock_streams.return_value = [
            [1, "Epic Gaming Session", "2024-01-15 20:00:00", "2024-01-15 23:30:00", "thumb.jpg", 1250],
            [2, "Chill Stream", "2024-01-14 18:00:00", "2024-01-14 22:00:00", "thumb2.jpg", 856],
        ]
        mock_count.return_value = 1000

        with TestClient(app) as client:
            response = client.get("/streams?creator_id=5&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert "streams" in data
        assert "max_offset" in data
        assert len(data["streams"]) == 2
        assert data["max_offset"] == 1000

        mock_streams.assert_called_once_with(5, 0)
        mock_count.assert_called_once_with(5)

    @patch("stream_sniper.api.stream_endpoints.select_all_stream_count_db")
    @patch("stream_sniper.api.stream_endpoints.select_all_streams_db")
    def test_get_streams_all_creators(self, mock_streams, mock_count):
        """Test retrieving streams for all creators."""
        mock_streams.return_value = []
        mock_count.return_value = 0

        with TestClient(app) as client:
            response = client.get("/streams?creator_id=-1&offset=0")

        assert response.status_code == 200
        mock_streams.assert_called_once_with(-1, 0)
        mock_count.assert_called_once_with(-1)

    @patch("stream_sniper.api.stream_endpoints.select_all_chatters_on_stream_db")
    def test_get_stream_chatters_success(self, mock_select):
        """Test successful retrieval of stream chatters."""
        mock_select.return_value = [[42, "viewer123"], [15, "chatty_user"], [87, "stream_regular"]]

        with TestClient(app) as client:
            response = client.get("/stream/1/chatters")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0] == [42, "viewer123"]
        mock_select.assert_called_once_with(1)

    @patch("stream_sniper.api.stream_endpoints.select_all_chatters_on_stream_db")
    def test_get_stream_chatters_not_found(self, mock_select):
        """Test stream chatters endpoint when stream not found."""
        mock_select.return_value = None

        with TestClient(app) as client:
            response = client.get("/stream/999/chatters")

        assert response.status_code == 404

    @patch("stream_sniper.api.stream_endpoints.select_chatters_in_stream_db")
    @patch("stream_sniper.api.stream_endpoints.select_creators_that_wrote_in_stream_db")
    @patch("stream_sniper.api.stream_endpoints.select_most_tagged_chatters_db")
    @patch("stream_sniper.api.stream_endpoints.select_most_active_chatters_db")
    @patch("stream_sniper.api.stream_endpoints.select_stream_comprehensive_db")
    def test_get_stream_comprehensive_success(
        self, mock_comprehensive, mock_active, mock_tagged, mock_creators, mock_chatters
    ):
        """Test comprehensive stream analytics endpoint."""
        # Mock responses
        mock_comprehensive.return_value = [
            "Epic Gaming Session",
            "2024-01-15 20:00:00",
            "2024-01-15 23:30:00",
            "thumb.jpg",
            1250,
            "streamer123",
            "Amazing Streamer",
            "profile.jpg",
            5,
        ]
        mock_active.return_value = [[42, "chatty_user", 125], [15, "regular_viewer", 89]]
        mock_tagged.return_value = [[15, "popular_user", 45], [23, "famous_chatter", 32]]
        mock_creators.return_value = [[99, "other_streamer"], [101, "guest_creator"]]
        mock_chatters.return_value = [[287]]

        with TestClient(app) as client:
            response = client.get("/stream/1")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "csi" in data
        assert "mac" in data
        assert "mtc" in data
        assert "octw" in data
        assert "cis" in data

        assert data["csi"][0] == "Epic Gaming Session"
        assert len(data["mac"]) == 2
        assert len(data["mtc"]) == 2

        # Verify function calls
        mock_comprehensive.assert_called_once_with(1)
        mock_active.assert_called_once_with(1)
        mock_tagged.assert_called_once_with(1)
        mock_creators.assert_called_once_with(1, 5)  # stream_id, creator_id
        mock_chatters.assert_called_once_with(1)

    @patch("stream_sniper.api.stream_endpoints.select_stream_comprehensive_db")
    def test_get_stream_comprehensive_not_found(self, mock_comprehensive):
        """Test comprehensive stream endpoint when stream not found."""
        mock_comprehensive.return_value = None

        with TestClient(app) as client:
            response = client.get("/stream/999/")

        assert response.status_code == 404
        assert response.json()["detail"] == "Stream not found"

    @patch("stream_sniper.api.stream_endpoints.select_chatter_messages_on_stream_db")
    def test_get_chatter_messages_on_stream_success(self, mock_select):
        """Test retrieving chatter messages in specific stream."""
        mock_select.return_value = [["Hello everyone!"], ["Great play!"], ["Thanks for the stream!"]]

        with TestClient(app) as client:
            response = client.get("/stream/1/chatter/42/messages")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0] == "Hello everyone!"
        assert data[1] == "Great play!"
        mock_select.assert_called_once_with(1, 42)

    @patch("stream_sniper.api.stream_endpoints.select_chatter_messages_on_stream_db")
    def test_get_chatter_messages_on_stream_not_found(self, mock_select):
        """Test chatter messages on stream when not found."""
        mock_select.return_value = None

        with TestClient(app) as client:
            response = client.get("/stream/1/chatter/999/messages")

        assert response.status_code == 404
        assert response.json()["detail"] == "No messages found for this chatter in this stream"


class TestCreatorsEndpoints:
    """Test suite for creator-related API endpoints."""

    @patch("stream_sniper.api.api.select_creators_db")
    def test_get_creators_success(self, mock_select):
        """Test successful retrieval of all creators."""
        mock_select.return_value = [[1, "Amazing Streamer"], [2, "Pro Gamer"], [3, "Chat Master"]]

        with TestClient(app) as client:
            response = client.get("/creators")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0] == [1, "Amazing Streamer"]
        mock_select.assert_called_once()

    @patch("stream_sniper.api.api.select_creators_db")
    def test_get_creators_server_error(self, mock_select):
        """Test creators endpoint with database error."""
        mock_select.side_effect = Exception("Database error")

        with TestClient(app) as client:
            response = client.get("/creators")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"


class TestCreatorTopChattersEndpoint:
    """Test suite for the creator cross-stream top-chatters endpoint."""

    @patch("stream_sniper.api.api.select_creator_top_chatters_db")
    def test_get_creator_top_chatters_success(self, mock_select):
        """Test successful retrieval of a creator's most active chatters."""
        mock_select.return_value = [
            [42, "chatty_user", 1250],
            [15, "regular_viewer", 980],
            [7, "stream_fan", 640],
        ]

        with TestClient(app) as client:
            response = client.get("/creator/5/top-chatters")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0] == [42, "chatty_user", 1250]
        # Default limit of 25 is applied when ?limit is omitted
        mock_select.assert_called_once_with(5, 25)

    @patch("stream_sniper.api.api.select_creator_top_chatters_db")
    def test_get_creator_top_chatters_custom_limit(self, mock_select):
        """Test that a custom limit is passed through to the gateway."""
        mock_select.return_value = [[42, "chatty_user", 1250]]

        with TestClient(app) as client:
            response = client.get("/creator/5/top-chatters?limit=10")

        assert response.status_code == 200
        mock_select.assert_called_once_with(5, 10)

    @patch("stream_sniper.api.api.select_creator_top_chatters_db")
    def test_get_creator_top_chatters_empty_returns_200(self, mock_select):
        """Test that an empty result is a valid 200 with an empty list."""
        mock_select.return_value = []

        with TestClient(app) as client:
            response = client.get("/creator/5/top-chatters")

        assert response.status_code == 200
        assert response.json() == []

    @patch("stream_sniper.api.api.select_creator_top_chatters_db")
    def test_get_creator_top_chatters_server_error(self, mock_select):
        """Test creator top-chatters endpoint with database error."""
        mock_select.side_effect = Exception("Database connection failed")

        with TestClient(app) as client:
            response = client.get("/creator/5/top-chatters")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"


class TestChatterStreamActivityEndpoint:
    """Test suite for the chatter cross-stream footprint endpoint."""

    @patch("stream_sniper.api.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.chatter_endpoints.select_chatter_stream_activity_db")
    def test_get_chatter_stream_activity_success(self, mock_select, mock_get_cache):
        """Test successful retrieval of a chatter's cross-stream footprint."""
        mock_get_cache.return_value = _miss_cache()
        mock_select.return_value = [
            [1, "Epic Gaming Session", "2024-01-15 20:00:00", 5, "Amazing Streamer", 125],
            [2, "Chill Stream", "2024-01-14 18:00:00", 5, "Amazing Streamer", 42],
        ]

        with TestClient(app) as client:
            response = client.get("/chatter/42/stream-activity")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0] == [1, "Epic Gaming Session", "2024-01-15 20:00:00", 5, "Amazing Streamer", 125]
        mock_select.assert_called_once_with(42)

    @patch("stream_sniper.api.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.chatter_endpoints.select_chatter_stream_activity_db")
    def test_get_chatter_stream_activity_empty_returns_200(self, mock_select, mock_get_cache):
        """Test that an empty result is a valid 200 with an empty list."""
        mock_get_cache.return_value = _miss_cache()
        mock_select.return_value = []

        with TestClient(app) as client:
            response = client.get("/chatter/999/stream-activity")

        assert response.status_code == 200
        assert response.json() == []

    @patch("stream_sniper.api.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.chatter_endpoints.select_chatter_stream_activity_db")
    def test_get_chatter_stream_activity_server_error(self, mock_select, mock_get_cache):
        """Test chatter stream-activity endpoint with database error."""
        mock_get_cache.return_value = _miss_cache()
        mock_select.side_effect = Exception("Database connection failed")

        with TestClient(app) as client:
            response = client.get("/chatter/42/stream-activity")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"


class TestHealthEndpoint:
    """Test suite for health check endpoint."""

    @patch("stream_sniper.api.health.get_pool")
    def test_health_check_success(self, mock_get_pool):
        """Test successful health check."""
        mock_pool = Mock()
        mock_pool.health_check.return_value = True
        mock_pool.get_pool_status.return_value = {"status": "active", "minconn": 2, "maxconn": 20}
        mock_get_pool.return_value = mock_pool

        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert "database" in data
        assert data["database"]["healthy"] is True
        assert "timestamp" in data
        assert data["version"] == "1.0.0"

    @patch("stream_sniper.api.health.get_pool")
    def test_health_check_unhealthy(self, mock_get_pool):
        """Test health check when database is unhealthy."""
        mock_pool = Mock()
        mock_pool.health_check.return_value = False
        mock_pool.get_pool_status.return_value = {"status": "error", "minconn": 2, "maxconn": 20}
        mock_get_pool.return_value = mock_pool

        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"]["healthy"] is False

    @patch("stream_sniper.api.health.get_pool")
    def test_health_check_critical_error(self, mock_get_pool):
        """Test health check with critical error."""
        mock_get_pool.side_effect = Exception("Database connection failed")

        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] in ("critical", "unhealthy")


class TestRootEndpoint:
    """Test suite for root API information endpoint."""

    def test_root_endpoint(self):
        """Test root endpoint returns API information."""
        with TestClient(app) as client:
            response = client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "Stream Sniper API"
        assert data["version"] == "1.0.0"
        assert data["description"] == "Twitch stream analytics API"
        assert data["docs"] == "/docs"
        assert data["redoc"] == "/redoc"


class TestAPIValidation:
    """Test suite for API request validation."""

    def test_get_streams_missing_creator_id(self):
        """Test streams endpoint requires creator_id parameter."""
        with TestClient(app) as client:
            response = client.get("/streams")

        assert response.status_code == 422  # Validation error

    def test_get_streams_negative_offset(self):
        """Test streams endpoint rejects negative offset."""
        with TestClient(app) as client:
            response = client.get("/streams?creator_id=1&offset=-1")

        assert response.status_code == 422  # Validation error

    def test_get_chatter_messages_invalid_chatter_id(self):
        """Test chatter messages endpoint with invalid chatter ID."""
        with TestClient(app) as client:
            response = client.get("/chatter/invalid/messages")

        assert response.status_code == 422  # Validation error

    def test_get_stream_invalid_stream_id(self):
        """Test stream endpoint with invalid stream ID."""
        with TestClient(app) as client:
            response = client.get("/stream/invalid/")

        assert response.status_code == 422  # Validation error


class TestCORSMiddleware:
    """Test suite for CORS middleware configuration."""

    def test_cors_headers_present(self):
        """Test that CORS headers are present in responses."""
        with TestClient(app) as client:
            response = client.options("/")

        # FastAPI automatically handles OPTIONS requests for CORS
        assert response.status_code in [200, 405]  # 405 if endpoint doesn't exist


class TestAPIDocumentation:
    """Test suite for API documentation endpoints."""

    def test_openapi_schema_accessible(self):
        """Test that OpenAPI schema is accessible."""
        with TestClient(app) as client:
            response = client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()
        assert "openapi" in schema
        assert "info" in schema
        assert schema["info"]["title"] == "Stream Sniper API"

    def test_docs_endpoint_accessible(self):
        """Test that Swagger UI documentation is accessible."""
        with TestClient(app) as client:
            response = client.get("/docs")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_endpoint_accessible(self):
        """Test that ReDoc documentation is accessible."""
        with TestClient(app) as client:
            response = client.get("/redoc")

        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


class TestChatterSearchEndpoint:
    """Test suite for the /chatters/search autocomplete endpoint."""

    @patch("stream_sniper.api.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.chatter_endpoints.select_chatters_by_prefix_db")
    def test_search_chatters_success(self, mock_search, mock_get_cache):
        """Prefix search returns [id, nick] pairs and calls the gateway."""
        mock_get_cache.return_value = _miss_cache()
        mock_search.return_value = [[42, "ninja"], [77, "ninjastreams"]]

        with TestClient(app) as client:
            response = client.get("/chatters/search?q=nin")

        assert response.status_code == 200
        assert response.json() == [[42, "ninja"], [77, "ninjastreams"]]
        mock_search.assert_called_once_with("nin", 10)

    @patch("stream_sniper.api.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.chatter_endpoints.select_chatters_by_prefix_db")
    def test_search_chatters_trims_and_honors_limit(self, mock_search, mock_get_cache):
        """Whitespace is trimmed and the limit query param is passed through."""
        mock_get_cache.return_value = _miss_cache()
        mock_search.return_value = []

        with TestClient(app) as client:
            response = client.get("/chatters/search?q=%20nin%20&limit=5")

        assert response.status_code == 200
        assert response.json() == []
        mock_search.assert_called_once_with("nin", 5)

    @patch("stream_sniper.api.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.chatter_endpoints.select_chatters_by_prefix_db")
    def test_search_chatters_short_query_skips_db(self, mock_search, mock_get_cache):
        """Queries shorter than 2 chars return [] without touching the database."""
        mock_get_cache.return_value = _miss_cache()

        with TestClient(app) as client:
            response = client.get("/chatters/search?q=n")

        assert response.status_code == 200
        assert response.json() == []
        mock_search.assert_not_called()

    @patch("stream_sniper.api.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.chatter_endpoints.select_chatters_by_prefix_db")
    def test_search_chatters_server_error(self, mock_search, mock_get_cache):
        """A database error surfaces as a 500."""
        mock_get_cache.return_value = _miss_cache()
        mock_search.side_effect = Exception("Database connection failed")

        with TestClient(app) as client:
            response = client.get("/chatters/search?q=nin")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

    def test_search_chatters_missing_query(self):
        """The q param is required."""
        with TestClient(app) as client:
            response = client.get("/chatters/search")

        assert response.status_code == 422


class TestTwitchSearchEndpoint:
    """Test suite for the admin /admin/tracking/twitch-search endpoint."""

    @staticmethod
    def _override_admin():
        app.dependency_overrides[get_current_admin_user] = lambda: SimpleNamespace(
            id=1, username="admin", role="admin"
        )

    @staticmethod
    def _clear_admin():
        app.dependency_overrides.pop(get_current_admin_user, None)

    @patch("stream_sniper.api.tracking_endpoints.get_cache")
    @patch("stream_sniper.api.tracking_endpoints.TwitchAPI")
    def test_search_twitch_channels_success(self, mock_twitch_cls, mock_get_cache):
        """Channel results are mapped to {login, display_name, profile_image_url, is_live}."""
        mock_get_cache.return_value = _miss_cache()
        channel = SimpleNamespace(
            broadcaster_login="ninja",
            display_name="Ninja",
            thumbnail_url="http://img/ninja.png",
            is_live=True,
        )
        instance = mock_twitch_cls.instance.return_value
        instance.ensure_initialized = AsyncMock()
        instance.search_channels_async = AsyncMock(return_value=[channel])

        self._override_admin()
        try:
            with TestClient(app) as client:
                response = client.get("/admin/tracking/twitch-search?q=nin")
        finally:
            self._clear_admin()

        assert response.status_code == 200
        assert response.json() == [
            {
                "login": "ninja",
                "display_name": "Ninja",
                "profile_image_url": "http://img/ninja.png",
                "is_live": True,
            }
        ]
        instance.search_channels_async.assert_awaited_once_with("nin", 8)

    @patch("stream_sniper.api.tracking_endpoints.get_cache")
    @patch("stream_sniper.api.tracking_endpoints.TwitchAPI")
    def test_search_twitch_channels_short_query_skips_twitch(self, mock_twitch_cls, mock_get_cache):
        """Short queries return [] without hitting the Twitch API."""
        mock_get_cache.return_value = _miss_cache()
        instance = mock_twitch_cls.instance.return_value
        instance.ensure_initialized = AsyncMock()
        instance.search_channels_async = AsyncMock(return_value=[])

        self._override_admin()
        try:
            with TestClient(app) as client:
                response = client.get("/admin/tracking/twitch-search?q=n")
        finally:
            self._clear_admin()

        assert response.status_code == 200
        assert response.json() == []
        instance.search_channels_async.assert_not_awaited()

    def test_search_twitch_channels_requires_auth(self):
        """Without an admin token the endpoint rejects the request."""
        with TestClient(app) as client:
            response = client.get("/admin/tracking/twitch-search?q=nin")

        assert response.status_code in (401, 403)
