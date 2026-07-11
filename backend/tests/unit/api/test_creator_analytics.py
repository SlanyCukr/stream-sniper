"""Unit tests for creator analytics endpoints (trends + regulars).

The analytics router is mounted onto a dedicated test app (its integration into
the main app is owned by a separate task), so these tests exercise the handlers
in isolation with mocked gateways and an always-miss cache.
"""

from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.analytics_endpoints import router
from stream_sniper.api.rate_limiter import setup_rate_limiting


def _build_app():
    app = FastAPI()
    setup_rate_limiting(app)
    app.include_router(router)
    return app


app = _build_app()


def _miss_cache():
    """A mock cache that always misses, so endpoint tests don't depend on cache state."""
    cache = Mock()
    cache._generate_key = Mock(side_effect=lambda *args: "-".join(str(a) for a in args))
    cache.get = Mock(return_value=None)
    cache.set = Mock(return_value=True)
    return cache


class TestCreatorTrendsEndpoint:
    """Test suite for GET /creator/{creator_id}/trends."""

    @patch("stream_sniper.api.analytics_endpoints.get_cache")
    @patch("stream_sniper.api.analytics_endpoints.select_creator_metrics_series_db")
    def test_trends_success_ascending(self, mock_series, mock_get_cache):
        """Trend points are returned in the gateway's order with default limit 20."""
        mock_get_cache.return_value = _miss_cache()
        mock_series.return_value = [
            (1, "Older Stream", "2024-01-10T20:00:00", 3600, 500, 8.33, 40, 30, 10),
            (2, "Newer Stream", "2024-01-15T20:00:00", 7200, 1200, 10.0, 90, 20, 70),
        ]

        with TestClient(app) as client:
            response = client.get("/creator/5/trends")

        assert response.status_code == 200
        data = response.json()
        assert data["creator_id"] == 5
        assert len(data["points"]) == 2
        assert data["points"][0]["stream_id"] == 1
        assert data["points"][0]["start"] == "2024-01-10T20:00:00"
        assert data["points"][1]["messages_per_minute"] == 10.0
        assert data["points"][1]["new_chatters"] == 20
        assert data["points"][1]["returning_chatters"] == 70
        mock_series.assert_called_once_with(5, 20)

    @patch("stream_sniper.api.analytics_endpoints.get_cache")
    @patch("stream_sniper.api.analytics_endpoints.select_creator_metrics_series_db")
    def test_trends_null_duration_serializes_null(self, mock_series, mock_get_cache):
        """A NULL duration_seconds from the gateway serializes as JSON null."""
        mock_get_cache.return_value = _miss_cache()
        mock_series.return_value = [
            (3, "Ongoing Stream", "2024-01-20T20:00:00", None, 100, 0.0, 20, 20, 0),
        ]

        with TestClient(app) as client:
            response = client.get("/creator/5/trends")

        assert response.status_code == 200
        data = response.json()
        assert data["points"][0]["duration_seconds"] is None
        assert data["points"][0]["message_count"] == 100

    @patch("stream_sniper.api.analytics_endpoints.get_cache")
    @patch("stream_sniper.api.analytics_endpoints.select_creator_metrics_series_db")
    def test_trends_custom_limit_forwarded(self, mock_series, mock_get_cache):
        """The limit query param is passed to the gateway."""
        mock_get_cache.return_value = _miss_cache()
        mock_series.return_value = []

        with TestClient(app) as client:
            response = client.get("/creator/5/trends?limit=50")

        assert response.status_code == 200
        assert response.json() == {"creator_id": 5, "points": []}
        mock_series.assert_called_once_with(5, 50)

    def test_trends_limit_over_max_422(self):
        """limit above 100 is rejected before the gateway."""
        with TestClient(app) as client:
            response = client.get("/creator/5/trends?limit=101")

        assert response.status_code == 422

    def test_trends_limit_below_min_422(self):
        """limit below 1 is rejected before the gateway."""
        with TestClient(app) as client:
            response = client.get("/creator/5/trends?limit=0")

        assert response.status_code == 422

    @patch("stream_sniper.api.analytics_endpoints.get_cache")
    @patch("stream_sniper.api.analytics_endpoints.select_creator_metrics_series_db")
    def test_trends_server_error(self, mock_series, mock_get_cache):
        """A gateway error surfaces as a 500."""
        mock_get_cache.return_value = _miss_cache()
        mock_series.side_effect = Exception("Database connection failed")

        with TestClient(app) as client:
            response = client.get("/creator/5/trends")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"


class TestCreatorRegularsEndpoint:
    """Test suite for GET /creator/{creator_id}/regulars."""

    @patch("stream_sniper.api.analytics_endpoints.get_cache")
    @patch("stream_sniper.api.analytics_endpoints.select_all_stream_count_db")
    @patch("stream_sniper.api.analytics_endpoints.select_creator_regulars_db")
    def test_regulars_attendance_rate_computed(self, mock_regulars, mock_count, mock_get_cache):
        """attendance_rate == round(streams_attended / total_streams, 4)."""
        mock_get_cache.return_value = _miss_cache()
        mock_count.return_value = 8
        mock_regulars.return_value = [
            (42, "chatty_user", 6, "2024-01-01T20:00:00", "2024-01-15T20:00:00", 99, 1250),
            (15, "regular_viewer", 3, "2024-01-02T20:00:00", "2024-01-14T20:00:00", 98, 640),
        ]

        with TestClient(app) as client:
            response = client.get("/creator/5/regulars?min_streams=1")

        assert response.status_code == 200
        data = response.json()
        assert data["creator_id"] == 5
        assert data["total_streams"] == 8
        assert len(data["regulars"]) == 2
        first = data["regulars"][0]
        assert first["chatter_id"] == 42
        assert first["nick"] == "chatty_user"
        assert first["streams_attended"] == 6
        assert first["attendance_rate"] == round(6 / 8, 4)
        assert first["first_seen"] == "2024-01-01T20:00:00"
        assert first["last_seen"] == "2024-01-15T20:00:00"
        assert first["last_stream_attended"] == 99
        assert first["message_count"] == 1250
        assert data["regulars"][1]["attendance_rate"] == round(3 / 8, 4)
        mock_count.assert_called_once_with(5)
        mock_regulars.assert_called_once_with(5, 1, 50, sort="attendance", dir="desc")

    @patch("stream_sniper.api.analytics_endpoints.get_cache")
    @patch("stream_sniper.api.analytics_endpoints.select_all_stream_count_db")
    @patch("stream_sniper.api.analytics_endpoints.select_creator_regulars_db")
    def test_regulars_zero_total_streams_no_zero_division(self, mock_regulars, mock_count, mock_get_cache):
        """total_streams == 0 yields attendance_rate 0.0 with no ZeroDivisionError."""
        mock_get_cache.return_value = _miss_cache()
        mock_count.return_value = 0
        mock_regulars.return_value = [
            (42, "chatty_user", 3, "2024-01-01T20:00:00", "2024-01-15T20:00:00", 99, 1250),
        ]

        with TestClient(app) as client:
            response = client.get("/creator/5/regulars")

        assert response.status_code == 200
        data = response.json()
        assert data["total_streams"] == 0
        assert data["regulars"][0]["attendance_rate"] == 0.0

    @patch("stream_sniper.api.analytics_endpoints.get_cache")
    @patch("stream_sniper.api.analytics_endpoints.select_all_stream_count_db")
    @patch("stream_sniper.api.analytics_endpoints.select_creator_regulars_db")
    def test_regulars_sort_and_dir_forwarded(self, mock_regulars, mock_count, mock_get_cache):
        """Whitelisted sort/dir are forwarded to the gateway as keyword args."""
        mock_get_cache.return_value = _miss_cache()
        mock_count.return_value = 10
        mock_regulars.return_value = []

        with TestClient(app) as client:
            response = client.get("/creator/5/regulars?sort=last_seen&dir=asc&min_streams=4&limit=25")

        assert response.status_code == 200
        mock_regulars.assert_called_once_with(5, 4, 25, sort="last_seen", dir="asc")

    def test_regulars_bogus_sort_422(self):
        """A sort value outside the whitelist is rejected before the gateway."""
        with TestClient(app) as client:
            response = client.get("/creator/5/regulars?sort=bogus")

        assert response.status_code == 422

    def test_regulars_sql_injection_sort_422(self):
        """A SQL-injection sort attempt 422s (whitelist guard)."""
        with TestClient(app) as client:
            response = client.get("/creator/5/regulars?sort=;DROP TABLE creator")

        assert response.status_code == 422

    def test_regulars_bad_dir_422(self):
        """An invalid dir value is rejected before the gateway."""
        with TestClient(app) as client:
            response = client.get("/creator/5/regulars?dir=sideways")

        assert response.status_code == 422

    def test_regulars_min_streams_out_of_range_422(self):
        """min_streams below 1 is rejected."""
        with TestClient(app) as client:
            response = client.get("/creator/5/regulars?min_streams=0")

        assert response.status_code == 422

    @patch("stream_sniper.api.analytics_endpoints.get_cache")
    @patch("stream_sniper.api.analytics_endpoints.select_all_stream_count_db")
    @patch("stream_sniper.api.analytics_endpoints.select_creator_regulars_db")
    def test_regulars_empty_returns_200(self, mock_regulars, mock_count, mock_get_cache):
        """No regulars is a valid 200 with an empty list."""
        mock_get_cache.return_value = _miss_cache()
        mock_count.return_value = 5
        mock_regulars.return_value = []

        with TestClient(app) as client:
            response = client.get("/creator/5/regulars")

        assert response.status_code == 200
        assert response.json() == {"creator_id": 5, "total_streams": 5, "regulars": []}

    @patch("stream_sniper.api.analytics_endpoints.get_cache")
    @patch("stream_sniper.api.analytics_endpoints.select_all_stream_count_db")
    @patch("stream_sniper.api.analytics_endpoints.select_creator_regulars_db")
    def test_regulars_server_error(self, mock_regulars, mock_count, mock_get_cache):
        """A gateway error surfaces as a 500."""
        mock_get_cache.return_value = _miss_cache()
        mock_count.return_value = 5
        mock_regulars.side_effect = Exception("Database connection failed")

        with TestClient(app) as client:
            response = client.get("/creator/5/regulars")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"
