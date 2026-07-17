"""Unit tests for the bounded stream-comparison endpoint."""

from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.features.streams.compare_endpoints import router
from stream_sniper.api.security.rate_limiter import setup_rate_limiting
from stream_sniper.application.streams.compare_query import normalize_curve
from stream_sniper.database.gateways.analytics.records import (
    StreamCompareBucketRow,
    StreamCompareHeaderRow,
    StreamPairRetentionRow,
)
from stream_sniper.database.gateways.streams.records import ViewerSampleRow


def _client():
    app = FastAPI()
    setup_rate_limiting(app)
    app.include_router(router)
    return TestClient(app)


def _cache():
    cache = Mock()
    cache.generate_key.return_value = "key"
    cache.get.return_value = None
    return cache


def test_compare_route_is_not_shadowed_by_stream_id_route():
    """Regression: /streams/compare must be registered before /streams/{stream_id}.

    With the wrong registration order the dynamic route captures the literal
    path segment "compare" and fails int path-param validation (422) before the
    comparison endpoint is ever reached — on the full app, not the router alone.
    """
    from stream_sniper.api.api import create_app
    from stream_sniper.api.config import APIConfig, AuthConfig

    app = create_app(APIConfig(auth=AuthConfig(secret_key="routing-test-secret")))
    response = TestClient(app).get("/streams/compare?stream_ids=1&stream_ids=2")

    assert not any(
        detail.get("loc") == ["path", "stream_id"]
        for detail in (response.json().get("detail") or [])
        if isinstance(detail, dict)
    ), f"/streams/compare was captured by /streams/{{stream_id}}: {response.text}"


def test_normalize_curve_uses_percentage_slots():
    rows = [
        StreamCompareBucketRow(1, "2024-01-01T20:00:00", 10, 5),
        StreamCompareBucketRow(1, "2024-01-01T20:05:00", 20, 8),
        StreamCompareBucketRow(1, "2024-01-01T20:10:00", 30, 10),
    ]
    points = normalize_curve(rows, "2024-01-01T20:00:00", 600)
    assert [point.percent for point in points] == [0, 50, 100]


@patch("stream_sniper.api.features.streams.compare_endpoints.get_cache")
@patch("stream_sniper.application.streams.compare_query.select_stream_pair_retention_db")
@patch("stream_sniper.application.streams.compare_query.select_stream_viewer_samples_db")
@patch("stream_sniper.application.streams.compare_query.select_stream_compare_buckets_db")
@patch("stream_sniper.application.streams.compare_query.select_stream_compare_headers_db")
def test_compare_maps_metrics_curve_and_retention(headers, buckets, samples, retention, get_cache):
    get_cache.return_value = _cache()
    headers.return_value = [
        StreamCompareHeaderRow(
            1,
            10,
            "a",
            "A",
            "One",
            "2024-01-01T20:00:00",
            600,
            100,
            10.0,
            20,
            8,
            12,
            25,
            50,
            30,
            "2024-01-01T20:05:00",
        ),
        StreamCompareHeaderRow(
            2,
            10,
            "a",
            "A",
            "Two",
            "2024-01-02T20:00:00",
            600,
            200,
            20.0,
            30,
            10,
            20,
            40,
            80,
            50,
            "2024-01-02T20:05:00",
        ),
    ]
    buckets.return_value = [
        StreamCompareBucketRow(1, "2024-01-01T20:00:00", 10, 5),
        StreamCompareBucketRow(2, "2024-01-02T20:00:00", 20, 8),
    ]
    samples.side_effect = [[ViewerSampleRow("x", 50)], [ViewerSampleRow("y", 80)]]
    retention.return_value = [StreamPairRetentionRow(1, 2, 20, 30, 12)]

    response = _client().get("/streams/compare?stream_ids=1&stream_ids=2")

    assert response.status_code == 200
    data = response.json()
    assert data["streams"][0]["sub_share"] == 0.25
    assert data["streams"][1]["peak_viewers"] == 80
    assert data["retention"][0]["retention_rate"] == 0.6


def test_compare_requires_unique_two_to_four_ids():
    assert _client().get("/streams/compare?stream_ids=1").status_code == 422
    assert _client().get("/streams/compare?stream_ids=1&stream_ids=1").status_code == 422
