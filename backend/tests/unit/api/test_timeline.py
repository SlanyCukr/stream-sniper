"""Unit tests for GET /stream/{stream_id}/timeline (§3.3).

The timeline router is not mounted on the shared ``app`` until the integration task (T9),
so these tests mount it on a minimal FastAPI app wired with the real rate limiter, then
patch the gateways by their import path in ``timeline_endpoints`` and use an always-miss cache.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.rate_limiter import setup_rate_limiting
from stream_sniper.api.timeline_endpoints import router

_BASE = datetime(2024, 1, 15, 20, 0, 0)


def _iso(minute_offset: int) -> str:
    return (_BASE + timedelta(minutes=minute_offset)).strftime("%Y-%m-%dT%H:%M:%S")


def _client() -> TestClient:
    app = FastAPI()
    setup_rate_limiting(app)
    app.include_router(router)
    return TestClient(app)


def _miss_cache():
    cache = Mock()
    cache._generate_key = Mock(return_value="test-cache-key")
    cache.get = Mock(return_value=None)
    cache.set = Mock(return_value=True)
    return cache


class TestTimelineEndpoint:
    @patch("stream_sniper.api.timeline_endpoints.get_cache")
    @patch("stream_sniper.api.timeline_endpoints.select_stream_header_db")
    @patch("stream_sniper.api.timeline_endpoints.select_stream_metrics_db")
    @patch("stream_sniper.api.timeline_endpoints.select_stream_buckets_db")
    def test_success_with_buckets_metrics_and_moments(
        self, mock_buckets, mock_metrics, mock_header, mock_get_cache
    ):
        mock_get_cache.return_value = _miss_cache()
        # Flat 5-msg baseline for minutes 0-9, then a clear spike at minute 10.
        buckets = [(_iso(i), 5, 3) for i in range(10)]
        buckets.append((_iso(10), 100, 40))
        mock_buckets.return_value = buckets
        mock_metrics.return_value = (105, 41, 3600, 1.75, 100, _iso(10), 30, 11)
        mock_header.return_value = (_iso(0), "vod12345")

        response = _client().get("/stream/7/timeline")

        assert response.status_code == 200
        data = response.json()
        assert data["stream_id"] == 7
        assert data["stream_start"] == _iso(0)
        assert data["twitch_id"] == "vod12345"
        assert data["bucket_seconds"] == 60
        assert len(data["buckets"]) == 11
        assert data["buckets"][10] == {
            "bucket_minute": _iso(10),
            "message_count": 100,
            "unique_chatters": 40,
        }
        assert data["metrics"] is not None
        assert data["metrics"]["total_messages"] == 105
        assert data["metrics"]["messages_per_minute"] == 1.75
        assert data["metrics"]["peak_bucket_minute"] == _iso(10)
        # One spike moment detected at minute 10.
        assert len(data["moments"]) == 1
        assert data["moments"][0]["bucket_minute"] == _iso(10)
        assert data["moments"][0]["message_count"] == 100
        assert data["moments"][0]["ratio"] == 20.0
        mock_buckets.assert_called_once_with(7)
        mock_metrics.assert_called_once_with(7)
        mock_header.assert_called_once_with(7)

    @patch("stream_sniper.api.timeline_endpoints.get_cache")
    @patch("stream_sniper.api.timeline_endpoints.select_stream_header_db")
    @patch("stream_sniper.api.timeline_endpoints.select_stream_metrics_db")
    @patch("stream_sniper.api.timeline_endpoints.select_stream_buckets_db")
    def test_empty_rollup_returns_200_with_null_metrics(
        self, mock_buckets, mock_metrics, mock_header, mock_get_cache
    ):
        mock_get_cache.return_value = _miss_cache()
        mock_buckets.return_value = []
        mock_metrics.return_value = None
        mock_header.return_value = None

        response = _client().get("/stream/99/timeline")

        assert response.status_code == 200
        data = response.json()
        assert data["stream_id"] == 99
        assert data["stream_start"] is None
        assert data["twitch_id"] is None
        assert data["bucket_seconds"] == 60
        assert data["buckets"] == []
        assert data["moments"] == []
        assert data["metrics"] is None

    @patch("stream_sniper.api.timeline_endpoints.get_cache")
    @patch("stream_sniper.api.timeline_endpoints.select_stream_header_db")
    @patch("stream_sniper.api.timeline_endpoints.select_stream_metrics_db")
    @patch("stream_sniper.api.timeline_endpoints.select_stream_buckets_db")
    def test_header_present_but_metrics_absent(
        self, mock_buckets, mock_metrics, mock_header, mock_get_cache
    ):
        mock_get_cache.return_value = _miss_cache()
        mock_buckets.return_value = [(_iso(0), 4, 2), (_iso(1), 6, 3)]
        mock_metrics.return_value = None
        mock_header.return_value = (_iso(0), "vod999")

        response = _client().get("/stream/5/timeline")

        assert response.status_code == 200
        data = response.json()
        assert data["metrics"] is None
        assert data["stream_start"] == _iso(0)
        assert data["twitch_id"] == "vod999"
        assert len(data["buckets"]) == 2

    @patch("stream_sniper.api.timeline_endpoints.get_cache")
    @patch("stream_sniper.api.timeline_endpoints.select_stream_header_db")
    @patch("stream_sniper.api.timeline_endpoints.select_stream_metrics_db")
    @patch("stream_sniper.api.timeline_endpoints.select_stream_buckets_db")
    def test_gateway_raise_returns_500(
        self, mock_buckets, mock_metrics, mock_header, mock_get_cache
    ):
        mock_get_cache.return_value = _miss_cache()
        mock_buckets.side_effect = Exception("db down")

        response = _client().get("/stream/7/timeline")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"
