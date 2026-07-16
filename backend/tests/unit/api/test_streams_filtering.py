"""Unit tests for the extended GET /streams sort/filter behavior (W1).

Mirrors the patch/TestClient patterns in test_api.py: patch get_cache with an
always-miss cache and patch each gateway by its import path in stream_endpoints,
then assert status + JSON shape + forwarded call args. A validation failure must
422 before the gateway is ever called (SQL-injection guard).
"""

from datetime import date
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from stream_sniper.api.asgi import app
from stream_sniper.database.gateways.streams.records import StreamListRow


def _miss_cache():
    """A mock cache that always misses, so endpoint tests don't depend on cache state."""
    cache = Mock()
    cache.generate_key = Mock(return_value="test-cache-key")
    cache.get = Mock(return_value=None)
    cache.set = Mock(return_value=True)
    return cache


class TestStreamsFiltering:
    """GET /streams sort/filter forwarding and validation."""

    @patch("stream_sniper.api.features.streams.stream_endpoints.get_cache")
    @patch("stream_sniper.api.composition.count_streams_db")
    @patch("stream_sniper.api.composition.select_stream_page_db")
    def test_defaults_unchanged(self, mock_streams, mock_count, mock_get_cache):
        """Bare request forwards the default sort/dir and all-None filters."""
        mock_get_cache.return_value = _miss_cache()
        mock_streams.return_value = []
        mock_count.return_value = 0

        with TestClient(app) as client:
            response = client.get("/streams?creator_id=5&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert data == {"streams": [], "total": 0, "offset": 0, "limit": 20}

        mock_streams.assert_called_once_with(
            5, 0, 20, sort="start", direction="desc", title=None, date_from=None, date_to=None, min_messages=None
        )
        mock_count.assert_called_once_with(5, title=None, date_from=None, date_to=None, min_messages=None)

    @patch("stream_sniper.api.features.streams.stream_endpoints.get_cache")
    @patch("stream_sniper.api.composition.count_streams_db")
    @patch("stream_sniper.api.composition.select_stream_page_db")
    def test_sort_and_dir_forwarded(self, mock_streams, mock_count, mock_get_cache):
        """sort/dir query params reach the row gateway (count ignores them)."""
        mock_get_cache.return_value = _miss_cache()
        mock_streams.return_value = []
        mock_count.return_value = 3

        with TestClient(app) as client:
            response = client.get("/streams?creator_id=5&sort=message_count&dir=asc")

        assert response.status_code == 200
        mock_streams.assert_called_once_with(
            5, 0, 20, sort="message_count", direction="asc", title=None, date_from=None, date_to=None, min_messages=None
        )
        # count query never receives sort/dir
        mock_count.assert_called_once_with(5, title=None, date_from=None, date_to=None, min_messages=None)

    @patch("stream_sniper.api.features.streams.stream_endpoints.get_cache")
    @patch("stream_sniper.api.composition.count_streams_db")
    @patch("stream_sniper.api.composition.select_stream_page_db")
    def test_filters_forwarded_to_both_gateways(self, mock_streams, mock_count, mock_get_cache):
        """title/date_from/date_to/min_messages reach BOTH gateways identically."""
        mock_get_cache.return_value = _miss_cache()
        mock_streams.return_value = []
        mock_count.return_value = 7

        with TestClient(app) as client:
            response = client.get(
                "/streams?creator_id=5&title=epic&date_from=2024-01-01&date_to=2024-01-31&min_messages=10"
            )

        assert response.status_code == 200
        mock_streams.assert_called_once_with(
            5,
            0,
            20,
            sort="start",
            direction="desc",
            title="epic",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            min_messages=10,
        )
        mock_count.assert_called_once_with(
            5,
            title="epic",
            date_from=date(2024, 1, 1),
            date_to=date(2024, 1, 31),
            min_messages=10,
        )

    @patch("stream_sniper.api.features.streams.stream_endpoints.get_cache")
    @patch("stream_sniper.api.composition.count_streams_db")
    @patch("stream_sniper.api.composition.select_stream_page_db")
    def test_count_respects_filters(self, mock_streams, mock_count, mock_get_cache):
        """total is the filtered count returned by the count gateway."""
        mock_get_cache.return_value = _miss_cache()
        mock_streams.return_value = [StreamListRow(1, "S", "2024-01-15 20:00:00", "2024-01-15 22:00:00", "t.jpg", 42)]
        mock_count.return_value = 1

        with TestClient(app) as client:
            response = client.get("/streams?creator_id=5&min_messages=40")

        assert response.status_code == 200
        assert response.json()["total"] == 1
        mock_count.assert_called_once_with(5, title=None, date_from=None, date_to=None, min_messages=40)

    @patch("stream_sniper.api.features.streams.stream_endpoints.get_cache")
    @patch("stream_sniper.api.composition.count_streams_db")
    @patch("stream_sniper.api.composition.select_stream_page_db")
    def test_sql_injection_sort_rejected(self, mock_streams, mock_count, mock_get_cache):
        """A malicious sort value 422s before any gateway is touched."""
        mock_get_cache.return_value = _miss_cache()

        with TestClient(app) as client:
            response = client.get("/streams?creator_id=5&sort=;DROP TABLE stream")

        assert response.status_code == 422
        mock_streams.assert_not_called()
        mock_count.assert_not_called()

    @patch("stream_sniper.api.features.streams.stream_endpoints.get_cache")
    @patch("stream_sniper.api.composition.count_streams_db")
    @patch("stream_sniper.api.composition.select_stream_page_db")
    def test_invalid_dir_rejected(self, mock_streams, mock_count, mock_get_cache):
        """An out-of-whitelist dir value 422s."""
        mock_get_cache.return_value = _miss_cache()

        with TestClient(app) as client:
            response = client.get("/streams?creator_id=5&dir=sideways")

        assert response.status_code == 422
        mock_streams.assert_not_called()
        mock_count.assert_not_called()

    @patch("stream_sniper.api.features.streams.stream_endpoints.get_cache")
    @patch("stream_sniper.api.composition.count_streams_db")
    @patch("stream_sniper.api.composition.select_stream_page_db")
    def test_negative_offset_rejected(self, mock_streams, mock_count, mock_get_cache):
        """offset<0 fails ge=0 validation."""
        mock_get_cache.return_value = _miss_cache()

        with TestClient(app) as client:
            response = client.get("/streams?creator_id=5&offset=-1")

        assert response.status_code == 422
        mock_streams.assert_not_called()

    @patch("stream_sniper.api.features.streams.stream_endpoints.get_cache")
    @patch("stream_sniper.api.composition.count_streams_db")
    @patch("stream_sniper.api.composition.select_stream_page_db")
    def test_negative_min_messages_rejected(self, mock_streams, mock_count, mock_get_cache):
        """min_messages<0 fails ge=0 validation."""
        mock_get_cache.return_value = _miss_cache()

        with TestClient(app) as client:
            response = client.get("/streams?creator_id=5&min_messages=-5")

        assert response.status_code == 422
        mock_streams.assert_not_called()

    @patch("stream_sniper.api.features.streams.stream_endpoints.get_cache")
    @patch("stream_sniper.api.composition.count_streams_db")
    @patch("stream_sniper.api.composition.select_stream_page_db")
    def test_gateway_raise_returns_500(self, mock_streams, mock_count, mock_get_cache):
        """A gateway exception surfaces as a 500 Internal server error."""
        mock_get_cache.return_value = _miss_cache()
        mock_streams.side_effect = Exception("db down")

        with TestClient(app) as client:
            response = client.get("/streams?creator_id=5")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"
