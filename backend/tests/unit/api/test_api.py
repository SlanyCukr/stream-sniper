"""
Unit tests for FastAPI endpoints.

Tests all API endpoints with mocked database responses to ensure:
- Correct HTTP status codes
- Proper response formatting
- Error handling
- Request validation
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.testclient import TestClient

from stream_sniper.api.asgi import app
from stream_sniper.api.dependencies import get_health_checker
from stream_sniper.api.features.auth.user_models import convert_user_to_response
from stream_sniper.api.observability.monitoring import MetricsCollector, RequestMetrics, record_request_metrics
from stream_sniper.api.security.auth import get_current_admin_user
from stream_sniper.api.security.rate_limiter import bind_rate_config_and_get_identifier, limiter, setup_rate_limiting
from stream_sniper.application.identity.tracked_streamer_creation import CreatorProfile
from stream_sniper.application.tracking.models import TrackedStreamer
from stream_sniper.collector.twitch_api import ArchivedVideo
from stream_sniper.database.gateways.chat.records import (
    ChatterIdentityRow,
    ChatterMessageRow,
    ChatterSearchRow,
    ChatterStreamActivityRow,
)
from stream_sniper.database.gateways.identity.records import (
    CreatorListRow,
    CreatorTopChatterRow,
    PublicUserRow,
    UserRow,
)
from stream_sniper.database.gateways.streams.records import (
    ChatterMessageTextRow,
    OtherCreatorRow,
    RankedChatterRow,
    StreamComprehensiveRow,
    StreamListRow,
    StreamParticipantRow,
)


def _miss_cache():
    """A mock cache that always misses, so endpoint tests don't depend on cache state."""
    cache = Mock()
    cache.generate_key = Mock(return_value="test-cache-key")
    cache.get = Mock(return_value=None)
    cache.set = Mock(return_value=True)
    return cache


class TestUserResponseConversion:
    """User rows from credential lookups must remain safe API responses."""

    def test_credential_bearing_user_row_converts_to_response(self):
        created_at = datetime(2026, 7, 9, 21, 0, 0)

        response = convert_user_to_response(
            UserRow(
                7,
                "admin_user",
                "admin@example.com",
                "$2b$12$password-hash",
                "admin",
                True,
                created_at,
            )
        )

        assert response.id == 7
        assert response.role == "admin"
        assert response.is_active is True
        assert response.created_at == created_at.isoformat()

    def test_public_user_row_converts_to_response(self):
        created_at = datetime(2026, 7, 9, 21, 0, 0)

        response = convert_user_to_response(
            PublicUserRow(
                8,
                "standard_user",
                "standard@example.com",
                "user",
                False,
                created_at,
            )
        )

        assert response.id == 8
        assert response.role == "user"
        assert response.is_active is False
        assert response.created_at == created_at.isoformat()


class TestChattersEndpoints:
    """Test suite for chatter-related API endpoints."""

    @patch("stream_sniper.api.features.chatters.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.select_chatter_message_count_db")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.select_chatter_messages_db")
    def test_get_chatter_messages_success(self, mock_select, mock_count, mock_get_cache):
        """Test successful retrieval of paginated chatter messages with stream context."""
        mock_get_cache.return_value = _miss_cache()
        mock_select.return_value = [
            ChatterMessageRow(7, "Epic Gaming Session", "SomeStreamer", "Hello everyone!", "2024-01-15 20:30:15"),
            ChatterMessageRow(8, "Chill Stream", "OtherStreamer", "Great stream!", "2024-01-14 20:45:22"),
        ]
        mock_count.return_value = 1234

        with TestClient(app) as client:
            response = client.get("/chatters/42/messages")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1234
        assert len(data["messages"]) == 2
        assert data["messages"][0] == {
            "stream_id": 7,
            "stream_title": "Epic Gaming Session",
            "creator_display_name": "SomeStreamer",
            "text": "Hello everyone!",
            "timestamp": "2024-01-15 20:30:15",
        }
        mock_select.assert_called_once_with(42, 50, 0)
        mock_count.assert_called_once_with(42)

    @patch("stream_sniper.api.features.chatters.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.select_chatter_message_count_db")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.select_chatter_messages_db")
    def test_get_chatter_messages_pagination_params(self, mock_select, mock_count, mock_get_cache):
        """Test that limit and offset query params are passed to the gateway."""
        mock_get_cache.return_value = _miss_cache()
        mock_select.return_value = []
        mock_count.return_value = 0

        with TestClient(app) as client:
            response = client.get("/chatters/42/messages?offset=100&limit=25")

        assert response.status_code == 200
        mock_select.assert_called_once_with(42, 25, 100)

    @patch("stream_sniper.api.features.chatters.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.select_chatter_message_count_db")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.select_chatter_messages_db")
    def test_get_chatter_messages_empty_returns_200(self, mock_select, mock_count, mock_get_cache):
        """Test that a chatter with no messages returns an empty page, not a 404."""
        mock_get_cache.return_value = _miss_cache()
        mock_select.return_value = []
        mock_count.return_value = 0

        with TestClient(app) as client:
            response = client.get("/chatters/999/messages")

        assert response.status_code == 200
        assert response.json() == {"messages": [], "total": 0, "offset": 0, "limit": 50}

    @patch("stream_sniper.api.features.chatters.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.select_chatter_message_count_db")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.select_chatter_messages_db")
    def test_get_chatter_messages_server_error(self, mock_select, mock_count, mock_get_cache):
        """Test chatter messages endpoint with database error."""
        mock_get_cache.return_value = _miss_cache()
        mock_select.side_effect = Exception("Database connection failed")

        with TestClient(app) as client:
            response = client.get("/chatters/42/messages")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

    @patch("stream_sniper.api.features.chatters.chatter_endpoints.select_chatter_identity_db")
    def test_get_chatter_id_success(self, mock_select):
        """Test successful retrieval of chatter ID."""
        mock_select.return_value = ChatterIdentityRow(42, None)

        with TestClient(app) as client:
            response = client.get("/chatters/by-nick/viewer123")

        assert response.status_code == 200
        assert response.json() == {"chatter_id": 42, "is_bot": None}
        mock_select.assert_called_once_with("viewer123")

    @patch("stream_sniper.api.features.chatters.chatter_endpoints.select_chatter_identity_db")
    def test_get_chatter_id_not_found(self, mock_select):
        """Test chatter ID endpoint when chatter not found."""
        mock_select.return_value = None

        with TestClient(app) as client:
            response = client.get("/chatters/by-nick/nonexistent")

        assert response.status_code == 404
        assert response.json()["detail"] == "Chatter not found"


class TestStreamsEndpoints:
    """Test suite for stream-related API endpoints."""

    @patch("stream_sniper.application.streams.catalog_query.count_streams_db")
    @patch("stream_sniper.application.streams.catalog_query.select_stream_page_db")
    def test_get_streams_success(self, mock_streams, mock_count):
        """Test successful retrieval of streams."""
        mock_streams.return_value = [
            StreamListRow(1, "Epic Gaming Session", "2024-01-15 20:00:00", "2024-01-15 23:30:00", "thumb.jpg", 1250),
            StreamListRow(2, "Chill Stream", "2024-01-14 18:00:00", "2024-01-14 22:00:00", "thumb2.jpg", 856),
        ]
        mock_count.return_value = 1000

        with TestClient(app) as client:
            response = client.get("/streams?creator_id=5&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert "streams" in data
        assert data["offset"] == 0
        assert data["limit"] == 20
        assert len(data["streams"]) == 2
        assert data["total"] == 1000
        assert data["streams"][0] == {
            "stream_id": 1,
            "creator_name": "Epic Gaming Session",
            "start": "2024-01-15 20:00:00",
            "end": "2024-01-15 23:30:00",
            "thumbnail_url": "thumb.jpg",
            "message_count": 1250,
        }

        mock_streams.assert_called_once_with(
            5, 0, 20, sort="start", direction="desc", title=None, date_from=None, date_to=None, min_messages=None
        )
        mock_count.assert_called_once_with(5, title=None, date_from=None, date_to=None, min_messages=None)

    @patch("stream_sniper.application.streams.catalog_query.count_streams_db")
    @patch("stream_sniper.application.streams.catalog_query.select_stream_page_db")
    def test_get_streams_all_creators(self, mock_streams, mock_count):
        """Test retrieving streams for all creators."""
        mock_streams.return_value = []
        mock_count.return_value = 0

        with TestClient(app) as client:
            response = client.get("/streams?creator_id=-1&offset=0")

        assert response.status_code == 200
        mock_streams.assert_called_once_with(
            -1, 0, 20, sort="start", direction="desc", title=None, date_from=None, date_to=None, min_messages=None
        )
        mock_count.assert_called_once_with(-1, title=None, date_from=None, date_to=None, min_messages=None)

    @patch("stream_sniper.api.features.streams.stream_endpoints.select_all_chatters_on_stream_db")
    def test_get_stream_chatters_success(self, mock_select):
        """Test successful retrieval of stream chatters."""
        mock_select.return_value = [
            StreamParticipantRow(42, "viewer123"),
            StreamParticipantRow(15, "chatty_user"),
            StreamParticipantRow(87, "stream_regular"),
        ]

        with TestClient(app) as client:
            response = client.get("/streams/1/chatters")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0] == {"chatter_id": 42, "nick": "viewer123"}
        mock_select.assert_called_once_with(1)

    @patch("stream_sniper.api.features.streams.stream_endpoints.select_all_chatters_on_stream_db")
    def test_get_stream_chatters_not_found(self, mock_select):
        """Test stream chatters endpoint when stream not found."""
        mock_select.return_value = None

        with TestClient(app) as client:
            response = client.get("/streams/999/chatters")

        assert response.status_code == 404

    @patch("stream_sniper.application.streams.catalog_query.select_chatters_in_stream_db")
    @patch("stream_sniper.application.streams.catalog_query.select_creators_that_wrote_in_stream_db")
    @patch("stream_sniper.application.streams.catalog_query.select_most_tagged_chatters_db")
    @patch("stream_sniper.application.streams.catalog_query.select_most_active_chatters_db")
    @patch("stream_sniper.application.streams.catalog_query.select_stream_comprehensive_db")
    def test_get_stream_comprehensive_success(
        self, mock_comprehensive, mock_active, mock_tagged, mock_creators, mock_chatters
    ):
        """Test comprehensive stream analytics endpoint."""
        # Mock responses
        mock_comprehensive.return_value = StreamComprehensiveRow(
            "Epic Gaming Session",
            "2024-01-15 20:00:00",
            "2024-01-15 23:30:00",
            "thumb.jpg",
            1250,
            "streamer123",
            "Amazing Streamer",
            "profile.jpg",
            5,
        )
        mock_active.return_value = [
            RankedChatterRow(42, "chatty_user", 125),
            RankedChatterRow(15, "regular_viewer", 89),
        ]
        mock_tagged.return_value = [
            RankedChatterRow(15, "popular_user", 45),
            RankedChatterRow(23, "famous_chatter", 32),
        ]
        mock_creators.return_value = [
            OtherCreatorRow(99, "other_streamer"),
            OtherCreatorRow(101, "guest_creator"),
        ]
        mock_chatters.return_value = [StreamParticipantRow(287, "viewer287")]

        with TestClient(app) as client:
            response = client.get("/streams/1")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert set(data) == {
            "info",
            "most_active_chatters",
            "most_tagged_chatters",
            "other_creators",
            "chatters",
        }
        assert data["info"]["title"] == "Epic Gaming Session"
        assert data["info"]["creator_id"] == 5
        assert len(data["most_active_chatters"]) == 2
        assert data["most_active_chatters"][0] == {
            "chatter_id": 42,
            "nick": "chatty_user",
            "count": 125,
        }

        # Verify function calls
        mock_comprehensive.assert_called_once_with(1)
        mock_active.assert_called_once_with(1)
        mock_tagged.assert_called_once_with(1)
        mock_creators.assert_called_once_with(1, 5)  # stream_id, creator_id
        mock_chatters.assert_called_once_with(1)

    @patch("stream_sniper.application.streams.catalog_query.select_stream_comprehensive_db")
    def test_get_stream_comprehensive_not_found(self, mock_comprehensive):
        """Test comprehensive stream endpoint when stream not found."""
        mock_comprehensive.return_value = None

        with TestClient(app) as client:
            response = client.get("/streams/999/")

        assert response.status_code == 404
        assert response.json()["detail"] == "Stream not found"

    @patch("stream_sniper.api.features.streams.stream_endpoints.select_chatter_messages_on_stream_db")
    def test_get_chatter_messages_on_stream_success(self, mock_select):
        """Test retrieving chatter messages in specific stream."""
        mock_select.return_value = [
            ChatterMessageTextRow("Hello everyone!"),
            ChatterMessageTextRow("Great play!"),
            ChatterMessageTextRow("Thanks for the stream!"),
        ]

        with TestClient(app) as client:
            response = client.get("/streams/1/chatters/42/messages")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0] == "Hello everyone!"
        assert data[1] == "Great play!"
        mock_select.assert_called_once_with(1, 42)

    @patch("stream_sniper.api.features.streams.stream_endpoints.select_chatter_messages_on_stream_db")
    def test_get_chatter_messages_on_stream_not_found(self, mock_select):
        """Test chatter messages on stream when not found."""
        mock_select.return_value = None

        with TestClient(app) as client:
            response = client.get("/streams/1/chatters/999/messages")

        assert response.status_code == 404
        assert response.json()["detail"] == "No messages found for this chatter in this stream"


class TestCreatorsEndpoints:
    """Test suite for creator-related API endpoints."""

    @patch("stream_sniper.api.features.creators.creator_endpoints.select_creators_db")
    def test_get_creators_success(self, mock_select):
        """Test successful retrieval of all creators."""
        mock_select.return_value = [
            CreatorListRow(1, "Amazing Streamer"),
            CreatorListRow(2, "Pro Gamer"),
            CreatorListRow(3, "Chat Master"),
        ]

        with TestClient(app) as client:
            response = client.get("/creators")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0] == {"creator_id": 1, "display_name": "Amazing Streamer"}
        mock_select.assert_called_once()

    @patch("stream_sniper.api.features.creators.creator_endpoints.select_creators_db")
    def test_get_creators_server_error(self, mock_select):
        """Test creators endpoint with database error."""
        mock_select.side_effect = Exception("Database error")

        with TestClient(app) as client:
            response = client.get("/creators")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"


class TestCreatorTopChattersEndpoint:
    """Test suite for the creator cross-stream top-chatters endpoint."""

    @patch("stream_sniper.api.features.creators.creator_endpoints.select_creator_top_chatters_db")
    def test_get_creator_top_chatters_success(self, mock_select):
        """Test successful retrieval of a creator's most active chatters."""
        mock_select.return_value = [
            CreatorTopChatterRow(42, "chatty_user", 1250),
            CreatorTopChatterRow(15, "regular_viewer", 980),
            CreatorTopChatterRow(7, "stream_fan", 640),
        ]

        with TestClient(app) as client:
            response = client.get("/creators/5/top-chatters")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert data[0] == {"chatter_id": 42, "nick": "chatty_user", "message_count": 1250}
        # Default limit of 25 is applied when ?limit is omitted
        mock_select.assert_called_once_with(5, 25)

    @patch("stream_sniper.api.features.creators.creator_endpoints.select_creator_top_chatters_db")
    def test_get_creator_top_chatters_custom_limit(self, mock_select):
        """Test that a custom limit is passed through to the gateway."""
        mock_select.return_value = [CreatorTopChatterRow(42, "chatty_user", 1250)]

        with TestClient(app) as client:
            response = client.get("/creators/5/top-chatters?limit=10")

        assert response.status_code == 200
        mock_select.assert_called_once_with(5, 10)

    @patch("stream_sniper.api.features.creators.creator_endpoints.select_creator_top_chatters_db")
    def test_get_creator_top_chatters_empty_returns_200(self, mock_select):
        """Test that an empty result is a valid 200 with an empty list."""
        mock_select.return_value = []

        with TestClient(app) as client:
            response = client.get("/creators/5/top-chatters")

        assert response.status_code == 200
        assert response.json() == []

    @patch("stream_sniper.api.features.creators.creator_endpoints.select_creator_top_chatters_db")
    def test_get_creator_top_chatters_server_error(self, mock_select):
        """Test creator top-chatters endpoint with database error."""
        mock_select.side_effect = Exception("Database connection failed")

        with TestClient(app) as client:
            response = client.get("/creators/5/top-chatters")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"


class TestChatterStreamActivityEndpoint:
    """Test suite for the chatter cross-stream footprint endpoint."""

    @patch("stream_sniper.api.features.chatters.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.select_chatter_stream_activity_db")
    def test_get_chatter_stream_activity_success(self, mock_select, mock_get_cache):
        """Test successful retrieval of a chatter's cross-stream footprint."""
        mock_get_cache.return_value = _miss_cache()
        mock_select.return_value = [
            ChatterStreamActivityRow(1, "Epic Gaming Session", "2024-01-15 20:00:00", 5, "Amazing Streamer", 125, None),
            ChatterStreamActivityRow(2, "Chill Stream", "2024-01-14 18:00:00", 5, "Amazing Streamer", 42, False),
        ]

        with TestClient(app) as client:
            response = client.get("/chatters/42/stream-activity")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0] == {
            "stream_id": 1,
            "stream_title": "Epic Gaming Session",
            "start": "2024-01-15 20:00:00",
            "creator_id": 5,
            "creator_display_name": "Amazing Streamer",
            "message_count": 125,
            "is_bot": None,
        }
        mock_select.assert_called_once_with(42)

    @patch("stream_sniper.api.features.chatters.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.select_chatter_stream_activity_db")
    def test_get_chatter_stream_activity_empty_returns_200(self, mock_select, mock_get_cache):
        """Test that an empty result is a valid 200 with an empty list."""
        mock_get_cache.return_value = _miss_cache()
        mock_select.return_value = []

        with TestClient(app) as client:
            response = client.get("/chatters/999/stream-activity")

        assert response.status_code == 200
        assert response.json() == []

    @patch("stream_sniper.api.features.chatters.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.select_chatter_stream_activity_db")
    def test_get_chatter_stream_activity_server_error(self, mock_select, mock_get_cache):
        """Test chatter stream-activity endpoint with database error."""
        mock_get_cache.return_value = _miss_cache()
        mock_select.side_effect = Exception("Database connection failed")

        with TestClient(app) as client:
            response = client.get("/chatters/42/stream-activity")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"


class TestHealthEndpoint:
    """Test suite for health check endpoint."""

    @patch("stream_sniper.api.observability.health.get_active_pool")
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

    @patch("stream_sniper.api.observability.health.get_active_pool")
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

    @patch("stream_sniper.api.observability.health.get_active_pool")
    def test_health_check_critical_error(self, mock_get_pool):
        """Test health check with critical error."""
        mock_get_pool.side_effect = Exception("Database connection failed")

        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 503
        data = response.json()
        assert data["status"] in ("critical", "unhealthy")


class TestOperationalEndpoints:
    """Public probes stay open while operational details fail closed."""

    def test_operational_endpoints_require_authentication(self):
        with TestClient(app) as client:
            responses = [
                client.get("/health/detailed"),
                client.get("/metrics/prometheus"),
                client.get("/metrics"),
                client.get("/cache/stats"),
                client.post("/cache/flush"),
            ]

        assert all(response.status_code in (401, 403) for response in responses)

    def test_public_health_failure_is_sanitized(self):
        failing_health = Mock()
        failing_health.get_basic_health.side_effect = RuntimeError("database password leaked")
        app.dependency_overrides[get_health_checker] = lambda: failing_health
        try:
            with TestClient(app) as client:
                response = client.get("/health")
        finally:
            app.dependency_overrides.pop(get_health_checker, None)

        assert response.status_code == 503
        assert response.json()["error"] == "Health check unavailable"
        assert "password" not in response.text

    def test_admin_can_reach_rate_limited_operational_endpoints(self):
        app.dependency_overrides[get_current_admin_user] = lambda: SimpleNamespace(id=1, username="admin", role="admin")
        try:
            with TestClient(app) as client:
                prometheus_response = client.get("/metrics/prometheus")
                metrics_response = client.get("/metrics")
                cache_stats_response = client.get("/cache/stats")
                cache_flush_response = client.post("/cache/flush")
        finally:
            app.dependency_overrides.pop(get_current_admin_user, None)

        assert prometheus_response.status_code == 200
        assert metrics_response.status_code == 200
        assert cache_stats_response.status_code == 200
        assert cache_flush_response.status_code == 200


class TestRateLimitingRuntime:
    """Rate-limit identity, responses, headers, and metrics share one real path."""

    def test_identifier_uses_client_ip_even_with_speculative_auth_headers(self):
        request = Request(
            {
                "type": "http",
                "http_version": "1.1",
                "method": "GET",
                "scheme": "http",
                "path": "/limited",
                "raw_path": b"/limited",
                "query_string": b"",
                "headers": [
                    (b"x-api-key", b"future-key"),
                    (b"authorization", b"Bearer future-token"),
                ],
                "client": ("203.0.113.8", 1234),
                "server": ("testserver", 80),
            }
        )

        assert bind_rate_config_and_get_identifier(request) == "ip:203.0.113.8"

    def test_repeated_request_returns_supported_429_and_records_metrics(self):
        test_app = FastAPI()

        @test_app.get("/limited")
        @limiter.limit("2/minute")
        def limited(request: Request, response: Response):
            return {"ok": True}

        setup_rate_limiting(test_app)

        @test_app.middleware("http")
        async def collect_request_metrics(request: Request, call_next):
            response = await call_next(request)
            record_request_metrics(
                collector,
                RequestMetrics(
                    endpoint=request.url.path,
                    method=request.method,
                    status_code=response.status_code,
                    response_time_ms=0.0,
                    timestamp=datetime.now(),
                    client_ip=request.client.host if request.client else "unknown",
                    rate_limited=response.status_code == 429,
                ),
            )
            return response

        collector = MetricsCollector()
        collector.reset_metrics()
        test_app.state.limiter.reset()
        try:
            with TestClient(test_app) as client:
                responses = [client.get("/limited") for _ in range(3)]
        finally:
            test_app.state.limiter.reset()

        assert [response.status_code for response in responses] == [200, 200, 429]
        assert responses[-1].json()["error"].startswith("Rate limit exceeded:")
        assert responses[-1].headers["retry-after"]
        assert responses[-1].headers["x-ratelimit-limit"] == "2"

        rate_metrics = collector.prune_and_summarize_metrics()["rate_limiting"]
        assert rate_metrics["total_requests"] == 3
        assert rate_metrics["rate_limited_requests"] == 1
        assert rate_metrics["endpoint_hits"] == {"/limited": 1}
        collector.reset_metrics()

    def test_independent_applications_do_not_share_rate_limit_counters(self):
        router = APIRouter()

        @router.get("/isolated")
        @limiter.limit("1/minute")
        def isolated(request: Request, response: Response):
            return {"ok": True}

        first = FastAPI()
        second = FastAPI()
        setup_rate_limiting(first)
        setup_rate_limiting(second)
        first.include_router(router)
        second.include_router(router)

        with TestClient(first) as first_client:
            first_responses = [first_client.get("/isolated") for _ in range(2)]
        with TestClient(second) as second_client:
            second_response = second_client.get("/isolated")

        assert [response.status_code for response in first_responses] == [200, 429]
        assert second_response.status_code == 200


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
            response = client.get("/chatters/invalid/messages")

        assert response.status_code == 422  # Validation error

    def test_get_stream_invalid_stream_id(self):
        """Test stream endpoint with invalid stream ID."""
        with TestClient(app) as client:
            response = client.get("/streams/invalid/")

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

    def test_custom_422_errors_document_business_and_framework_shapes(self):
        schema = app.openapi()
        expected = [
            {"$ref": "#/components/schemas/ErrorResponse"},
            {"$ref": "#/components/schemas/ValidationErrorResponse"},
        ]
        operations = [
            ("/streams/{stream_id}/messages", "get"),
            ("/streams/compare", "get"),
            ("/streams/{stream_id}/moments/{bucket_minute}/review", "put"),
            ("/scene/leaderboard", "get"),
        ]

        for path, method in operations:
            response_schema = schema["paths"][path][method]["responses"]["422"]["content"]["application/json"]["schema"]
            assert response_schema["anyOf"] == expected

    def test_administrative_failures_use_shared_response_schema(self):
        schema = app.openapi()
        expected = {"$ref": "#/components/schemas/ErrorResponse"}
        operations = [
            ("/auth/me", "put", "500"),
            ("/auth/me/password", "put", "500"),
            ("/auth/users/{user_id}/role", "put", "500"),
            ("/auth/users/{user_id}/activate", "put", "500"),
            ("/auth/users/{user_id}/deactivate", "put", "500"),
            ("/auth/users/{user_id}", "delete", "400"),
            ("/auth/users/{user_id}", "put", "500"),
            ("/admin/tracking/twitch-search", "get", "502"),
            ("/admin/tracking/streamers", "get", "500"),
        ]

        for path, method, status_code in operations:
            assert (
                schema["paths"][path][method]["responses"][status_code]["content"]["application/json"]["schema"]
                == expected
            )

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

    @patch("stream_sniper.api.features.chatters.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.select_chatters_by_prefix_db")
    def test_search_chatters_success(self, mock_search, mock_get_cache):
        """Prefix search returns [id, nick] pairs and calls the gateway."""
        mock_get_cache.return_value = _miss_cache()
        mock_search.return_value = [ChatterSearchRow(42, "ninja", None), ChatterSearchRow(77, "ninjastreams", False)]

        with TestClient(app) as client:
            response = client.get("/chatters/search?q=nin")

        assert response.status_code == 200
        assert response.json() == [
            {"chatter_id": 42, "nick": "ninja", "is_bot": None},
            {"chatter_id": 77, "nick": "ninjastreams", "is_bot": False},
        ]
        mock_search.assert_called_once_with("nin", 10)

    @patch("stream_sniper.api.features.chatters.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.select_chatters_by_prefix_db")
    def test_search_chatters_trims_and_honors_limit(self, mock_search, mock_get_cache):
        """Whitespace is trimmed and the limit query param is passed through."""
        mock_get_cache.return_value = _miss_cache()
        mock_search.return_value = []

        with TestClient(app) as client:
            response = client.get("/chatters/search?q=%20nin%20&limit=5")

        assert response.status_code == 200
        assert response.json() == []
        mock_search.assert_called_once_with("nin", 5)

    @patch("stream_sniper.api.features.chatters.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.select_chatters_by_prefix_db")
    def test_search_chatters_short_query_skips_db(self, mock_search, mock_get_cache):
        """Queries shorter than 2 chars return [] without touching the database."""
        mock_get_cache.return_value = _miss_cache()

        with TestClient(app) as client:
            response = client.get("/chatters/search?q=n")

        assert response.status_code == 200
        assert response.json() == []
        mock_search.assert_not_called()

    @patch("stream_sniper.api.features.chatters.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.select_chatters_by_prefix_db")
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
        app.dependency_overrides[get_current_admin_user] = lambda: SimpleNamespace(id=1, username="admin", role="admin")

    @staticmethod
    def _clear_admin():
        app.dependency_overrides.pop(get_current_admin_user, None)

    @patch("stream_sniper.api.features.tracking.tracking_streamer_endpoints.get_cache")
    @patch("stream_sniper.api.features.tracking.tracking_streamer_endpoints.get_twitch_client")
    def test_search_twitch_channels_success(self, mock_twitch_cls, mock_get_cache):
        """Channel results are mapped to {login, display_name, profile_image_url, is_live}."""
        mock_get_cache.return_value = _miss_cache()
        channel = SimpleNamespace(
            broadcaster_login="ninja",
            display_name="Ninja",
            thumbnail_url="http://img/ninja.png",
            is_live=True,
        )
        instance = mock_twitch_cls.return_value
        instance.ensure_initialized = AsyncMock()
        instance.search_channels = AsyncMock(return_value=[channel])

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
        instance.search_channels.assert_awaited_once_with("nin", 8)

    @patch("stream_sniper.api.features.tracking.tracking_streamer_endpoints.get_cache")
    @patch("stream_sniper.api.features.tracking.tracking_streamer_endpoints.get_twitch_client")
    def test_search_twitch_channels_short_query_skips_twitch(self, mock_twitch_cls, mock_get_cache):
        """Short queries return [] without hitting the Twitch API."""
        mock_get_cache.return_value = _miss_cache()
        instance = mock_twitch_cls.return_value
        instance.ensure_initialized = AsyncMock()
        instance.search_channels = AsyncMock(return_value=[])

        self._override_admin()
        try:
            with TestClient(app) as client:
                response = client.get("/admin/tracking/twitch-search?q=n")
        finally:
            self._clear_admin()

        assert response.status_code == 200
        assert response.json() == []
        instance.search_channels.assert_not_awaited()

    def test_search_twitch_channels_requires_auth(self):
        """Without an admin token the endpoint rejects the request."""
        with TestClient(app) as client:
            response = client.get("/admin/tracking/twitch-search?q=nin")

        assert response.status_code in (401, 403)


class TestTriggerProcessingEndpoint:
    """Test suite for POST /admin/tracking/streamers/{id}/process.

    The handler must reuse the process-wide TwitchAPI singleton with a
    per-call login instead of constructing a client (per-request OAuth) or
    mutating the singleton's shared nickname state.
    """

    @staticmethod
    def _override_admin():
        app.dependency_overrides[get_current_admin_user] = lambda: SimpleNamespace(id=1, username="admin", role="admin")

    @staticmethod
    def _clear_admin():
        app.dependency_overrides.pop(get_current_admin_user, None)

    @patch("stream_sniper.application.tracking.manual_processing.enqueue_processing_job_db")
    @patch("stream_sniper.application.tracking.manual_processing.select_existing_twitch_vod_ids_db")
    @patch("stream_sniper.application.tracking.manual_processing.select_tracked_streamer_by_id_db")
    @patch("stream_sniper.api.features.tracking.tracking_job_endpoints.get_twitch_client")
    def test_trigger_processing_queues_newest_uncollected_vod(
        self, mock_twitch_cls, mock_select_streamer, mock_select_stream, mock_enqueue_job
    ):
        """The newest not-yet-collected VOD is queued via the shared client."""
        now = datetime(2026, 7, 9, 12, 0, 0)
        mock_select_streamer.return_value = TrackedStreamer(
            7,
            1,
            "teststreamer",
            "TestStreamer",
            True,
            None,
            None,
            True,
            now,
            now,
            1,
            None,
            "TestStreamer",
            None,
            "admin",
        )
        instance = mock_twitch_cls.return_value
        instance.ensure_initialized = AsyncMock()
        instance.get_archived_videos = AsyncMock(
            return_value=[ArchivedVideo(111, None, datetime(2024, 1, 15, 20), "newest vod", "1h", "")]
        )
        mock_select_stream.return_value = set()  # not collected yet
        mock_enqueue_job.return_value = 42

        self._override_admin()
        try:
            with TestClient(app) as client:
                response = client.post("/admin/tracking/streamers/7/process")
        finally:
            self._clear_admin()

        assert response.status_code == 200
        body = response.json()
        assert body["queued"] is True
        assert body["job_id"] == 42
        assert body["twitch_vod_id"] == 111
        # Shared client reused, initialized idempotently, login passed per call.
        mock_twitch_cls.assert_called_once()
        instance.ensure_initialized.assert_awaited_once()
        instance.get_archived_videos.assert_awaited_once_with("teststreamer")
        mock_enqueue_job.assert_called_once_with(7, 111)

    @patch("stream_sniper.application.tracking.manual_processing.select_tracked_streamer_by_id_db")
    @patch("stream_sniper.api.features.tracking.tracking_job_endpoints.get_twitch_client")
    def test_trigger_processing_unknown_streamer_404(self, mock_twitch_cls, mock_select_streamer):
        """A missing streamer 404s before any Twitch call."""
        mock_select_streamer.return_value = None

        self._override_admin()
        try:
            with TestClient(app) as client:
                response = client.post("/admin/tracking/streamers/999/process")
        finally:
            self._clear_admin()

        assert response.status_code == 404
        mock_twitch_cls.assert_not_called()


class TestAddTrackedStreamerEndpoint:
    """Creator bootstrap in POST /admin/tracking/streamers must not mutate the
    shared TwitchAPI singleton's nickname state."""

    @staticmethod
    def _override_admin():
        app.dependency_overrides[get_current_admin_user] = lambda: SimpleNamespace(id=1, username="admin", role="admin")

    @staticmethod
    def _clear_admin():
        app.dependency_overrides.pop(get_current_admin_user, None)

    @patch("stream_sniper.application.identity.tracked_streamer_creation.select_tracked_streamer_by_id_db")
    @patch("stream_sniper.application.identity.tracked_streamer_creation.insert_tracked_streamer_db")
    @patch("stream_sniper.application.identity.tracked_streamer_creation.find_or_insert_creator_id_db")
    @patch("stream_sniper.application.identity.tracked_streamer_creation.select_creator_id_db")
    @patch("stream_sniper.application.identity.tracked_streamer_creation.streamer_exists_db")
    @patch("stream_sniper.api.features.tracking.tracking_streamer_endpoints.get_twitch_client")
    def test_add_streamer_bootstraps_creator_with_per_call_login(
        self,
        mock_twitch_cls,
        mock_exists,
        mock_select_creator,
        mock_insert_creator,
        mock_insert_streamer,
        mock_select_streamer,
    ):
        """A new creator is fetched from Twitch with an explicit login argument."""
        from datetime import datetime

        mock_exists.return_value = False
        mock_select_creator.return_value = None
        instance = mock_twitch_cls.return_value
        instance.ensure_initialized = AsyncMock()
        instance.get_creator_profile = AsyncMock(return_value=CreatorProfile("555", "NewStreamer", "http://img/p.png"))
        mock_insert_creator.return_value = 3
        mock_insert_streamer.return_value = 9
        now = datetime(2026, 7, 9, 12, 0, 0)
        mock_select_streamer.return_value = TrackedStreamer(
            9,
            3,
            "newstreamer",
            "NewStreamer",
            True,
            None,
            None,
            True,
            now,
            now,
            1,
            None,
            "NewStreamer",
            "http://img/p.png",
            "admin",
        )

        self._override_admin()
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/admin/tracking/streamers",
                    json={"twitch_username": "newstreamer"},
                )
        finally:
            self._clear_admin()

        assert response.status_code == 201
        assert response.json()["twitch_username"] == "newstreamer"
        instance.get_creator_profile.assert_awaited_once_with("newstreamer")
        mock_insert_creator.assert_called_once_with("newstreamer", "NewStreamer", "http://img/p.png", "555")

    @patch("stream_sniper.application.identity.tracked_streamer_creation.select_creator_id_db")
    @patch("stream_sniper.application.identity.tracked_streamer_creation.streamer_exists_db")
    @patch("stream_sniper.api.features.tracking.tracking_streamer_endpoints.get_twitch_client")
    def test_add_streamer_unknown_twitch_login_400(self, mock_twitch_cls, mock_exists, mock_select_creator):
        """A login Twitch doesn't know yields a specific 400, not a TypeError-driven one."""
        mock_exists.return_value = False
        mock_select_creator.return_value = None
        instance = mock_twitch_cls.return_value
        instance.ensure_initialized = AsyncMock()
        instance.get_creator_profile = AsyncMock(return_value=None)

        self._override_admin()
        try:
            with TestClient(app) as client:
                response = client.post(
                    "/admin/tracking/streamers",
                    json={"twitch_username": "nosuchlogin"},
                )
        finally:
            self._clear_admin()

        assert response.status_code == 400
        assert response.json()["detail"] == "Streamer not found on Twitch"
