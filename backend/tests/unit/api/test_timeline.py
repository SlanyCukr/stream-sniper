"""Unit tests for GET /stream/{stream_id}/timeline (§3.3).

The timeline router is not mounted on the shared ``app`` until the integration task, so these
tests mount it on a minimal FastAPI app wired with the real rate limiter, then patch the
gateways by their import path in ``timeline_endpoints`` and use an always-miss cache.

Gateway results use named persistence records so tests exercise the production contract.
"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.error_boundary import UnexpectedExceptionMiddleware
from stream_sniper.api.features.streams.timeline_endpoints import router
from stream_sniper.api.security.rate_limiter import setup_rate_limiting
from stream_sniper.database.gateways.analytics.records import (
    StreamBucketRow,
    StreamHeaderRow,
    StreamMetricsRow,
)
from stream_sniper.database.gateways.content.records import StreamMomentRow
from stream_sniper.database.gateways.streams.records import (
    StreamContextChangeRow,
    ViewerSampleRow,
)

_BASE = datetime(2024, 1, 15, 20, 0, 0)


@pytest.fixture(autouse=True)
def _empty_context_changes(monkeypatch):
    monkeypatch.setattr(
        "stream_sniper.application.streams.timeline_query.select_stream_context_changes_db",
        lambda _stream_id: [],
    )


def _iso(minute_offset: int) -> str:
    return (_BASE + timedelta(minutes=minute_offset)).strftime("%Y-%m-%dT%H:%M:%S")


def _client() -> TestClient:
    app = FastAPI()
    setup_rate_limiting(app)
    app.add_middleware(UnexpectedExceptionMiddleware)
    app.include_router(router)
    return TestClient(app)


def _miss_cache():
    cache = Mock()
    cache.generate_key = Mock(return_value="test-cache-key")
    cache.get = Mock(return_value=None)
    cache.set = Mock(return_value=True)
    return cache


class TestTimelineEndpoint:
    @patch("stream_sniper.api.features.streams.timeline_endpoints.get_cache")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_viewer_samples_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_moments_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_header_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_metrics_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_buckets_db")
    def test_success_with_buckets_metrics_and_moments(
        self, mock_buckets, mock_metrics, mock_header, mock_moments, mock_samples, mock_get_cache
    ):
        mock_get_cache.return_value = _miss_cache()
        # Flat 5-msg baseline for minutes 0-9, then a clear spike at minute 10.
        buckets = [StreamBucketRow(_iso(i), 5, 3, 2, 1) for i in range(10)]
        buckets.append(StreamBucketRow(_iso(10), 100, 40, 30, 25))
        mock_buckets.return_value = buckets
        mock_metrics.return_value = StreamMetricsRow(105, 41, 3600, 1.75, 100, _iso(10), 30, 11, 60, 45)
        mock_header.return_value = StreamHeaderRow(_iso(0), "vod12345")
        mock_moments.return_value = []  # no persisted moments -> live fallback detection
        mock_samples.return_value = []

        response = _client().get("/streams/7/timeline")

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
            "sub_messages": 30,
            "emote_messages": 25,
        }
        assert data["metrics"] is not None
        assert data["metrics"]["total_messages"] == 105
        assert data["metrics"]["messages_per_minute"] == 1.75
        assert data["metrics"]["peak_bucket_minute"] == _iso(10)
        assert data["metrics"]["sub_messages"] == 60
        assert data["metrics"]["emote_messages"] == 45
        # One spike moment detected at minute 10 via the live fallback (no enrichment fields).
        assert len(data["moments"]) == 1
        assert data["moments"][0]["bucket_minute"] == _iso(10)
        assert data["moments"][0]["message_count"] == 100
        assert data["moments"][0]["ratio"] == 20.0
        assert data["moments"][0]["status"] is None
        assert data["moments"][0]["persisted"] is False  # live detect_moments fallback
        assert data["moments"][0]["sub_share"] is None
        assert data["moments"][0]["top_phrases"] is None
        assert data["viewer_samples"] == []
        assert data["peak_viewers"] is None
        mock_buckets.assert_called_once_with(7)
        mock_metrics.assert_called_once_with(7)
        mock_header.assert_called_once_with(7)
        mock_moments.assert_called_once_with(7)
        mock_samples.assert_called_once_with(7)

    @patch("stream_sniper.api.features.streams.timeline_endpoints.get_cache")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_viewer_samples_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_moments_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_header_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_metrics_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_buckets_db")
    def test_empty_rollup_returns_200_with_null_metrics(
        self, mock_buckets, mock_metrics, mock_header, mock_moments, mock_samples, mock_get_cache
    ):
        mock_get_cache.return_value = _miss_cache()
        mock_buckets.return_value = []
        mock_metrics.return_value = None
        mock_header.return_value = None
        mock_moments.return_value = []
        mock_samples.return_value = []

        response = _client().get("/streams/99/timeline")

        assert response.status_code == 200
        data = response.json()
        assert data["stream_id"] == 99
        assert data["stream_start"] is None
        assert data["twitch_id"] is None
        assert data["bucket_seconds"] == 60
        assert data["buckets"] == []
        assert data["moments"] == []
        assert data["metrics"] is None
        assert data["viewer_samples"] == []
        assert data["peak_viewers"] is None

    @patch("stream_sniper.api.features.streams.timeline_endpoints.get_cache")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_viewer_samples_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_moments_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_header_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_metrics_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_buckets_db")
    def test_header_present_but_metrics_absent(
        self, mock_buckets, mock_metrics, mock_header, mock_moments, mock_samples, mock_get_cache
    ):
        mock_get_cache.return_value = _miss_cache()
        mock_buckets.return_value = [
            StreamBucketRow(_iso(0), 4, 2, 1, 0),
            StreamBucketRow(_iso(1), 6, 3, 2, 1),
        ]
        mock_metrics.return_value = None
        mock_header.return_value = StreamHeaderRow(_iso(0), "vod999")
        mock_moments.return_value = []
        mock_samples.return_value = []

        response = _client().get("/streams/5/timeline")

        assert response.status_code == 200
        data = response.json()
        assert data["metrics"] is None
        assert data["stream_start"] == _iso(0)
        assert data["twitch_id"] == "vod999"
        assert len(data["buckets"]) == 2

    @patch("stream_sniper.api.features.streams.timeline_endpoints.get_cache")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_viewer_samples_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_moments_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_header_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_metrics_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_buckets_db")
    def test_gateway_raise_returns_500(
        self, mock_buckets, mock_metrics, mock_header, mock_moments, mock_samples, mock_get_cache
    ):
        mock_get_cache.return_value = _miss_cache()
        mock_buckets.side_effect = Exception("db down")

        response = _client().get("/streams/7/timeline")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

    @patch("stream_sniper.api.features.streams.timeline_endpoints.get_cache")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_viewer_samples_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_moments_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_header_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_metrics_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_buckets_db")
    def test_zero_fill_synthesizes_missing_minutes(
        self, mock_buckets, mock_metrics, mock_header, mock_moments, mock_samples, mock_get_cache
    ):
        mock_get_cache.return_value = _miss_cache()
        # Observed only at minute 0 and minute 3 -> minutes 1 and 2 must be synthesized.
        mock_buckets.return_value = [
            StreamBucketRow(_iso(0), 4, 2, 1, 0),
            StreamBucketRow(_iso(3), 7, 5, 3, 2),
        ]
        mock_metrics.return_value = None
        mock_header.return_value = StreamHeaderRow(_iso(0), "vod1")
        mock_moments.return_value = []
        mock_samples.return_value = []

        response = _client().get("/streams/1/timeline")

        assert response.status_code == 200
        buckets = response.json()["buckets"]
        assert len(buckets) == 4
        assert [b["bucket_minute"] for b in buckets] == [_iso(i) for i in range(4)]
        # Observed minute 0 keeps its real (possibly-zero) metadata.
        assert buckets[0]["emote_messages"] == 0
        # Synthesized minutes are zero for counts but None (unknown) for sub/emote metadata.
        assert buckets[1] == {
            "bucket_minute": _iso(1),
            "message_count": 0,
            "unique_chatters": 0,
            "sub_messages": None,
            "emote_messages": None,
        }
        assert buckets[2]["message_count"] == 0
        assert buckets[2]["sub_messages"] is None
        assert buckets[3]["message_count"] == 7

    @patch("stream_sniper.api.features.streams.timeline_endpoints.get_cache")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_viewer_samples_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_moments_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_header_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_metrics_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_buckets_db")
    def test_persisted_moments_used_when_present(
        self, mock_buckets, mock_metrics, mock_header, mock_moments, mock_samples, mock_get_cache
    ):
        mock_get_cache.return_value = _miss_cache()
        # Flat buckets: live detection would find NO spike, so any moment proves the
        # persisted path was taken.
        mock_buckets.return_value = [StreamBucketRow(_iso(i), 5, 3, 1, 1) for i in range(5)]
        mock_metrics.return_value = None
        mock_header.return_value = StreamHeaderRow(_iso(0), "vod1")
        mock_moments.return_value = [
            StreamMomentRow(
                _iso(2),
                120,
                420,
                80.0,
                5.25,
                40,
                0.3125,
                0.5,
                [{"phrase": "pog", "count": 12, "lift": 4.2}],
                [{"text": "POG", "count": 8}],
                "bookmarked",
                None,
                None,
            )
        ]
        mock_samples.return_value = []

        response = _client().get("/streams/1/timeline")

        assert response.status_code == 200
        moments = response.json()["moments"]
        assert len(moments) == 1
        m = moments[0]
        assert m["bucket_minute"] == _iso(2)
        assert m["offset_seconds"] == 120
        assert m["message_count"] == 420
        assert m["ratio"] == 5.25
        assert m["sub_share"] == 0.3125
        assert m["emote_share"] == 0.5
        assert m["top_phrases"] == [{"phrase": "pog", "count": 12, "lift": 4.2}]
        assert m["sample_messages"] == [{"text": "POG", "count": 8}]
        assert m["status"] == "bookmarked"
        assert m["persisted"] is True  # read from persisted stream_moment

    @patch("stream_sniper.api.features.streams.timeline_endpoints.get_cache")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_viewer_samples_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_moments_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_header_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_metrics_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_buckets_db")
    def test_viewer_samples_and_peak(
        self, mock_buckets, mock_metrics, mock_header, mock_moments, mock_samples, mock_get_cache
    ):
        mock_get_cache.return_value = _miss_cache()
        mock_buckets.return_value = [StreamBucketRow(_iso(0), 4, 2, 1, 0)]
        mock_metrics.return_value = None
        mock_header.return_value = StreamHeaderRow(_iso(0), "vod1")
        mock_moments.return_value = []
        mock_samples.return_value = [
            ViewerSampleRow(_iso(0), 1200),
            ViewerSampleRow(_iso(5), 3400),
            ViewerSampleRow(_iso(10), 2100),
        ]

        response = _client().get("/streams/1/timeline")

        assert response.status_code == 200
        data = response.json()
        assert data["viewer_samples"] == [
            {"t": _iso(0), "viewer_count": 1200},
            {"t": _iso(5), "viewer_count": 3400},
            {"t": _iso(10), "viewer_count": 2100},
        ]
        assert data["peak_viewers"] == 3400

    @patch("stream_sniper.api.features.streams.timeline_endpoints.get_cache")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_viewer_samples_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_moments_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_header_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_metrics_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_buckets_db")
    def test_metrics_sub_emote_null_passthrough(
        self, mock_buckets, mock_metrics, mock_header, mock_moments, mock_samples, mock_get_cache
    ):
        mock_get_cache.return_value = _miss_cache()
        mock_buckets.return_value = [StreamBucketRow(_iso(0), 4, 2, None, None)]
        # Not yet re-rolled under 0008: sub/emote metadata is NULL, not 0.
        mock_metrics.return_value = StreamMetricsRow(10, 5, 600, 1.0, 4, _iso(0), 5, 0, None, None)
        mock_header.return_value = StreamHeaderRow(_iso(0), "vod1")
        mock_moments.return_value = []
        mock_samples.return_value = []

        response = _client().get("/streams/1/timeline")

        assert response.status_code == 200
        data = response.json()
        # Unknown metadata stays None (never coerced to 0).
        assert data["metrics"]["sub_messages"] is None
        assert data["metrics"]["emote_messages"] is None
        assert data["buckets"][0]["sub_messages"] is None
        assert data["buckets"][0]["emote_messages"] is None

    @patch("stream_sniper.api.features.streams.timeline_endpoints.get_cache")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_viewer_samples_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_moments_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_header_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_metrics_db")
    @patch("stream_sniper.application.streams.timeline_query.select_stream_buckets_db")
    def test_context_changes_are_exposed(
        self,
        mock_buckets,
        mock_metrics,
        mock_header,
        mock_moments,
        mock_samples,
        mock_get_cache,
        monkeypatch,
    ):
        mock_get_cache.return_value = _miss_cache()
        mock_buckets.return_value = [StreamBucketRow(_iso(0), 4, 2, 0, 0)]
        mock_metrics.return_value = None
        mock_header.return_value = StreamHeaderRow(_iso(0), "vod1")
        mock_moments.return_value = []
        mock_samples.return_value = []
        monkeypatch.setattr(
            "stream_sniper.application.streams.timeline_query.select_stream_context_changes_db",
            lambda _stream_id: [
                StreamContextChangeRow(_iso(0), "Opening", "509658", "Just Chatting", "en", ["English"], False),
            ],
        )

        response = _client().get("/streams/1/timeline")

        assert response.status_code == 200
        assert response.json()["context_changes"] == [
            {
                "t": _iso(0),
                "title": "Opening",
                "category_id": "509658",
                "category_name": "Just Chatting",
                "language": "en",
                "tags": ["English"],
                "is_mature": False,
            }
        ]
