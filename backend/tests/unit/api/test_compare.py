"""Unit tests for the bounded stream-comparison endpoint."""

from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.compare_endpoints import _normalise_curve, router
from stream_sniper.api.rate_limiter import setup_rate_limiting


def _client():
    app = FastAPI()
    setup_rate_limiting(app)
    app.include_router(router)
    return TestClient(app)


def _cache():
    cache = Mock()
    cache._generate_key.return_value = "key"
    cache.get.return_value = None
    return cache


def test_normalise_curve_uses_percentage_slots():
    rows = [
        (1, "2024-01-01T20:00:00", 10, 5),
        (1, "2024-01-01T20:05:00", 20, 8),
        (1, "2024-01-01T20:10:00", 30, 10),
    ]
    points = _normalise_curve(rows, "2024-01-01T20:00:00", 600)
    assert [point.percent for point in points] == [0, 50, 100]


@patch("stream_sniper.api.compare_endpoints.get_cache")
@patch("stream_sniper.api.compare_endpoints.select_stream_pair_retention_db")
@patch("stream_sniper.api.compare_endpoints.select_stream_viewer_samples_db")
@patch("stream_sniper.api.compare_endpoints.select_stream_compare_buckets_db")
@patch("stream_sniper.api.compare_endpoints.select_stream_compare_headers_db")
def test_compare_maps_metrics_curve_and_retention(headers, buckets, samples, retention, get_cache):
    get_cache.return_value = _cache()
    headers.return_value = [
        (1, 10, "a", "A", "One", "2024-01-01T20:00:00", 600, 100, 10.0, 20, 8, 12, 25, 50, 30, "2024-01-01T20:05:00"),
        (2, 10, "a", "A", "Two", "2024-01-02T20:00:00", 600, 200, 20.0, 30, 10, 20, 40, 80, 50, "2024-01-02T20:05:00"),
    ]
    buckets.return_value = [
        (1, "2024-01-01T20:00:00", 10, 5),
        (2, "2024-01-02T20:00:00", 20, 8),
    ]
    samples.side_effect = [[("x", 50)], [("y", 80)]]
    retention.return_value = [(1, 2, 20, 30, 12)]

    response = _client().get("/streams/compare?stream_ids=1&stream_ids=2")

    assert response.status_code == 200
    data = response.json()
    assert data["streams"][0]["sub_share"] == 0.25
    assert data["streams"][1]["peak_viewers"] == 80
    assert data["retention"][0]["retention_rate"] == 0.6


def test_compare_requires_unique_two_to_four_ids():
    assert _client().get("/streams/compare?stream_ids=1").status_code == 422
    assert _client().get("/streams/compare?stream_ids=1&stream_ids=1").status_code == 422
