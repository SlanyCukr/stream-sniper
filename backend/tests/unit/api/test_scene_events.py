"""API tests for the scene pulse and digest preview."""

from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.error_boundary import UnexpectedExceptionMiddleware
from stream_sniper.api.features.content.scene_event_endpoints import router
from stream_sniper.api.security.rate_limiter import setup_rate_limiting
from stream_sniper.database.gateways.content.records import SceneEventRow


def _client():
    app = FastAPI()
    app.add_middleware(UnexpectedExceptionMiddleware)
    setup_rate_limiting(app)
    app.include_router(router)
    return TestClient(app)


@patch("stream_sniper.api.features.content.scene_event_endpoints.get_cache")
@patch("stream_sniper.api.features.content.scene_event_endpoints.select_scene_events_db")
def test_pulse_maps_rows(events, get_cache):
    cache = Mock()
    cache.generate_key.return_value = "key"
    cache.get.return_value = None
    get_cache.return_value = cache
    events.return_value = (
        [
            SceneEventRow(
                1,
                "personal_record",
                "2024-01-02T22:00:00",
                5,
                "alice",
                "Alice",
                42,
                None,
                "New record",
                "2,000",
                {"metric": "messages"},
            )
        ],
        1,
    )

    response = _client().get("/scene/pulse?days=7&event_type=personal_record")

    assert response.status_code == 200
    assert response.json()["items"][0]["creator_display_name"] == "Alice"
    events.assert_called_once_with(7, "personal_record", None, 50, 0)


@patch("stream_sniper.api.features.content.scene_event_endpoints.build_digest", return_value="## digest")
def test_digest_preview(build):
    response = _client().get("/scene/digest?days=7")
    assert response.status_code == 200
    assert response.json() == {"days": 7, "markdown": "## digest"}
    build.assert_called_once_with(7)
