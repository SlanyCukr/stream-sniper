"""Unit tests for windowed audience participation movement."""

from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.audience_endpoints import router
from stream_sniper.api.rate_limiter import setup_rate_limiting


def _client():
    app = FastAPI()
    setup_rate_limiting(app)
    app.include_router(router)
    return TestClient(app)


@patch("stream_sniper.api.audience_endpoints.get_cache")
@patch("stream_sniper.api.audience_endpoints.select_creator_audience_movement_db")
def test_audience_movement_maps_window_and_associations(gateway, get_cache):
    cache = Mock()
    cache._generate_key.return_value = "key"
    cache.get.return_value = None
    get_cache.return_value = cache
    gateway.return_value = (
        (100, 80, 60, 40, 20),
        [(2, "source", "Source", 12)],
        [(3, "dest", "Destination", 8)],
    )

    response = _client().get("/creator/5/audience-movement?days=30")

    assert response.status_code == 200
    data = response.json()
    assert data["retention_rate"] == 0.75
    assert data["gain_rate"] == 0.4
    assert data["prior_channels_for_gained"][0]["creator_id"] == 2
    gateway.assert_called_once_with(5, 30, 8)


def test_audience_window_is_bounded():
    assert _client().get("/creator/5/audience-movement?days=6").status_code == 422
    assert _client().get("/creator/5/audience-movement?days=91").status_code == 422
