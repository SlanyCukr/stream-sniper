"""Unit tests for the W2 stream message replay endpoint (GET /stream/{id}/messages)."""

from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.message_endpoints import router
from stream_sniper.api.rate_limiter import setup_rate_limiting


def _build_app():
    """Mount only the replay router on a fresh app (api.py mount is a separate task)."""
    app = FastAPI()
    setup_rate_limiting(app)
    app.include_router(router)
    return app


app = _build_app()


def _miss_cache():
    cache = Mock()
    cache._generate_key = Mock(return_value="test-cache-key")
    cache.get = Mock(return_value=None)
    cache.set = Mock(return_value=True)
    return cache


class TestStreamMessageReplay:
    @patch("stream_sniper.api.message_endpoints.get_cache")
    @patch("stream_sniper.api.message_endpoints.select_stream_messages_db")
    def test_first_page_short_has_no_next_cursor(self, mock_select, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_select.return_value = [
            (1, "2024-01-15T20:30:15", 42, "alice", "hello", True, "subscriber/12"),
            (2, "2024-01-15T20:30:20", 43, "bob", "hi", None, None),
        ]

        with TestClient(app) as client:
            response = client.get("/stream/7/messages?limit=100")

        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 2
        assert data["messages"][0] == {
            "id": 1,
            "time": "2024-01-15T20:30:15",
            "chatter_id": 42,
            "nick": "alice",
            "text": "hello",
            "is_subscriber": True,
            "badges": "subscriber/12",
        }
        # legacy rows (pre-0007) carry NULL metadata
        assert data["messages"][1]["is_subscriber"] is None
        assert data["messages"][1]["badges"] is None
        assert data["next_cursor"] is None
        assert data["has_more"] is False
        mock_select.assert_called_once_with(
            7, 100, after_ts=None, after_id=None, chatter_id=None, q=None, sub_only=False
        )

    @patch("stream_sniper.api.message_endpoints.get_cache")
    @patch("stream_sniper.api.message_endpoints.select_stream_messages_db")
    def test_full_page_returns_cursor_from_last_row(self, mock_select, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_select.return_value = [
            (10, "2024-01-15T20:30:15", 42, "alice", "a", False, None),
            (11, "2024-01-15T20:30:16", 43, "bob", "b", True, "moderator/1"),
        ]

        with TestClient(app) as client:
            response = client.get("/stream/7/messages?limit=2")

        assert response.status_code == 200
        data = response.json()
        assert data["next_cursor"] == {"after_ts": "2024-01-15T20:30:16", "after_id": 11}
        assert data["has_more"] is True

    @patch("stream_sniper.api.message_endpoints.get_cache")
    @patch("stream_sniper.api.message_endpoints.select_stream_messages_db")
    def test_cursor_round_trip_forwards_after_params(self, mock_select, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_select.return_value = []

        with TestClient(app) as client:
            response = client.get(
                "/stream/7/messages?after_ts=2024-01-15T20:30:16&after_id=11&limit=50"
            )

        assert response.status_code == 200
        mock_select.assert_called_once_with(
            7, 50, after_ts="2024-01-15T20:30:16", after_id=11, chatter_id=None, q=None, sub_only=False
        )

    @patch("stream_sniper.api.message_endpoints.get_cache")
    @patch("stream_sniper.api.message_endpoints.select_stream_messages_db")
    def test_chatter_and_query_filters_forwarded(self, mock_select, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_select.return_value = []

        with TestClient(app) as client:
            response = client.get("/stream/7/messages?chatter_id=42&q=lol")

        assert response.status_code == 200
        mock_select.assert_called_once_with(
            7, 100, after_ts=None, after_id=None, chatter_id=42, q="lol", sub_only=False
        )

    @patch("stream_sniper.api.message_endpoints.get_cache")
    @patch("stream_sniper.api.message_endpoints.select_stream_messages_db")
    def test_sub_only_filter_forwarded_to_gateway(self, mock_select, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_select.return_value = []

        with TestClient(app) as client:
            response = client.get("/stream/7/messages?sub_only=true")

        assert response.status_code == 200
        mock_select.assert_called_once_with(
            7, 100, after_ts=None, after_id=None, chatter_id=None, q=None, sub_only=True
        )

    @patch("stream_sniper.api.message_endpoints.get_cache")
    @patch("stream_sniper.api.message_endpoints.select_stream_messages_db")
    def test_sub_only_included_in_cache_key(self, mock_select, mock_get_cache):
        cache = _miss_cache()
        mock_get_cache.return_value = cache
        mock_select.return_value = []

        with TestClient(app) as client:
            client.get("/stream/7/messages?sub_only=true")
            key_args_true = cache._generate_key.call_args[0]
            cache._generate_key.reset_mock()
            client.get("/stream/7/messages?sub_only=false")
            key_args_false = cache._generate_key.call_args[0]

        # sub_only participates in the cache key, so the two requests key differently
        assert True in key_args_true
        assert False in key_args_false
        assert key_args_true != key_args_false

    @patch("stream_sniper.api.message_endpoints.get_cache")
    @patch("stream_sniper.api.message_endpoints.select_stream_messages_db")
    def test_empty_page_returns_200(self, mock_select, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_select.return_value = []

        with TestClient(app) as client:
            response = client.get("/stream/7/messages")

        assert response.status_code == 200
        data = response.json()
        assert data["messages"] == []
        assert data["next_cursor"] is None
        assert data["has_more"] is False

    def test_limit_above_max_is_422(self):
        with TestClient(app) as client:
            response = client.get("/stream/7/messages?limit=500")
        assert response.status_code == 422

    def test_limit_zero_is_422(self):
        with TestClient(app) as client:
            response = client.get("/stream/7/messages?limit=0")
        assert response.status_code == 422

    @patch("stream_sniper.api.message_endpoints.get_cache")
    @patch("stream_sniper.api.message_endpoints.select_stream_messages_db")
    def test_gateway_error_returns_500(self, mock_select, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_select.side_effect = Exception("db down")

        with TestClient(app) as client:
            response = client.get("/stream/7/messages")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"
