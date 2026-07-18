"""Unit tests for the public scene-wide Highlights Wall endpoint.

The highlights router is mounted onto a dedicated test app with the real limiter, and the
gateway + cache + rollup-version probe are patched at the endpoint module's import path.
Postgres is never touched (the rejected-exclusion / window boundaries are asserted at the
SQL level in the scratch-DB check, not here).
"""

from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.error_boundary import UnexpectedExceptionMiddleware
from stream_sniper.api.features.content.scene_highlights_endpoints import router
from stream_sniper.api.security.rate_limiter import setup_rate_limiting
from stream_sniper.database.gateways.content.scene_highlights_gateway import SceneHighlightRow

_GW = "stream_sniper.api.features.content.scene_highlights_endpoints.select_scene_highlights_db"
_CACHE = "stream_sniper.api.features.content.scene_highlights_endpoints.get_cache"
_VERSION = "stream_sniper.api.features.content.scene_highlights_endpoints.scene_rollup_version"


def _build_app():
    app = FastAPI()
    setup_rate_limiting(app)
    app.add_middleware(UnexpectedExceptionMiddleware)
    app.include_router(router)
    return app


app = _build_app()


def _miss_cache():
    """A mock cache that always misses, so endpoint tests don't depend on cache state."""
    cache = Mock()
    cache.generate_key = Mock(side_effect=lambda *args: "-".join(str(a) for a in args))
    cache.get = Mock(return_value=None)
    cache.set = Mock(return_value=True)
    return cache


def _hit_cache(payload):
    """A mock cache that returns `payload` on get (cache HIT)."""
    cache = Mock()
    cache.generate_key = Mock(side_effect=lambda *args: "-".join(str(a) for a in args))
    cache.get = Mock(return_value=payload)
    cache.set = Mock(return_value=True)
    return cache


def _row(**overrides):
    base = {
        "stream_id": 42,
        "stream_title": "Ranked grind",
        "twitch_id": 998877,
        "creator_id": 5,
        "creator_nick": "streamer",
        "creator_display_name": "Streamer",
        "bucket_minute": "2024-01-01T20:05:00",
        "offset_seconds": 300,
        "ratio": 4.5,
        "message_count": 220,
        "unique_chatters": 88,
        "sub_share": 0.25,
        "emote_share": 0.6,
        "top_phrases": [{"phrase": "KEKW", "count": 40, "lift": 3.2}],
        "sample_messages": [{"text": "KEKW KEKW", "count": 12}],
        "clip_url": None,
        "review_status": None,
    }
    base.update(overrides)
    return SceneHighlightRow(**base)


class TestSceneHighlightsSuccess:
    """GET /scene/highlights — happy paths and shaping."""

    @patch(_VERSION, return_value="v1")
    @patch(_GW)
    @patch(_CACHE)
    def test_default_shape_and_defaults_forwarded(self, mock_get_cache, mock_gw, _mock_ver):
        """Default query returns the full Highlight shape; defaults forward as (None, None, hype, 24, 0)."""
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = ([_row()], False)

        response = TestClient(app).get("/scene/highlights")

        assert response.status_code == 200
        assert response.headers["X-Cache"] == "MISS"
        data = response.json()
        assert data["window"] == "all"
        assert data["sort"] == "hype"
        assert data["has_more"] is False
        item = data["items"][0]
        assert item == {
            "stream_id": 42,
            "stream_title": "Ranked grind",
            "twitch_id": "998877",  # bigint rendered as string
            "creator_id": 5,
            "creator_nick": "streamer",
            "creator_display_name": "Streamer",
            "bucket_minute": "2024-01-01T20:05:00",
            "offset_seconds": 300,
            "ratio": 4.5,
            "message_count": 220,
            "unique_chatters": 88,
            "sub_share": 0.25,
            "emote_share": 0.6,
            "top_phrases": [{"phrase": "KEKW", "count": 40, "lift": 3.2}],
            "sample_messages": [{"text": "KEKW KEKW", "count": 12}],
            "clip_url": None,
            "review_status": None,
        }
        mock_gw.assert_called_once_with(None, None, "hype", 24, 0)

    @patch(_VERSION, return_value="v1")
    @patch(_GW)
    @patch(_CACHE)
    def test_nullable_fields_and_twitch_none_preserved(self, mock_get_cache, mock_gw, _mock_ver):
        """NULL ratio/sub_share/emote_share and a null twitch_id stay null (never coalesced)."""
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = (
            [_row(twitch_id=None, ratio=None, sub_share=None, emote_share=None, top_phrases=None, sample_messages=None)],
            False,
        )

        response = TestClient(app).get("/scene/highlights")

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["twitch_id"] is None
        assert item["ratio"] is None
        assert item["sub_share"] is None
        assert item["emote_share"] is None
        assert item["top_phrases"] is None
        assert item["sample_messages"] is None

    @patch(_VERSION, return_value="v1")
    @patch(_GW)
    @patch(_CACHE)
    def test_review_fields_surface(self, mock_get_cache, mock_gw, _mock_ver):
        """A curated (clipped) moment surfaces clip_url + review_status."""
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = ([_row(clip_url="https://clips.twitch.tv/abc", review_status="clipped")], False)

        response = TestClient(app).get("/scene/highlights")

        item = response.json()["items"][0]
        assert item["clip_url"] == "https://clips.twitch.tv/abc"
        assert item["review_status"] == "clipped"

    @patch(_VERSION, return_value="v1")
    @patch(_GW)
    @patch(_CACHE)
    def test_empty_returns_200(self, mock_get_cache, mock_gw, _mock_ver):
        """No moments is a valid 200 with an empty list and has_more false."""
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = ([], False)

        response = TestClient(app).get("/scene/highlights")

        assert response.status_code == 200
        assert response.json() == {"window": "all", "sort": "hype", "items": [], "has_more": False}


class TestSceneHighlightsFilters:
    """Query parameters map through to the gateway."""

    @patch(_VERSION, return_value="v1")
    @patch(_GW)
    @patch(_CACHE)
    def test_window_7_maps_to_window_days_7(self, mock_get_cache, mock_gw, _mock_ver):
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = ([], False)

        response = TestClient(app).get("/scene/highlights?window=7")

        assert response.status_code == 200
        assert response.json()["window"] == "7"
        mock_gw.assert_called_once_with(7, None, "hype", 24, 0)

    @patch(_VERSION, return_value="v1")
    @patch(_GW)
    @patch(_CACHE)
    def test_window_30_maps_to_window_days_30(self, mock_get_cache, mock_gw, _mock_ver):
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = ([], False)

        response = TestClient(app).get("/scene/highlights?window=30")

        assert response.status_code == 200
        mock_gw.assert_called_once_with(30, None, "hype", 24, 0)

    @patch(_VERSION, return_value="v1")
    @patch(_GW)
    @patch(_CACHE)
    def test_sort_recent_and_creator_and_pagination_forwarded(self, mock_get_cache, mock_gw, _mock_ver):
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = ([], True)

        response = TestClient(app).get("/scene/highlights?window=7&creator_id=9&sort=recent&limit=10&offset=20")

        assert response.status_code == 200
        assert response.json()["sort"] == "recent"
        assert response.json()["has_more"] is True
        mock_gw.assert_called_once_with(7, 9, "recent", 10, 20)


class TestSceneHighlightsValidation:
    """Invalid query parameters are rejected before the gateway (422)."""

    def test_bad_window_422(self):
        response = TestClient(app).get("/scene/highlights?window=5")
        assert response.status_code == 422

    def test_bad_sort_422(self):
        response = TestClient(app).get("/scene/highlights?sort=bogus")
        assert response.status_code == 422

    def test_limit_over_max_422(self):
        response = TestClient(app).get("/scene/highlights?limit=51")
        assert response.status_code == 422

    def test_limit_below_min_422(self):
        response = TestClient(app).get("/scene/highlights?limit=0")
        assert response.status_code == 422

    def test_negative_offset_422(self):
        response = TestClient(app).get("/scene/highlights?offset=-1")
        assert response.status_code == 422

    def test_creator_id_zero_422(self):
        response = TestClient(app).get("/scene/highlights?creator_id=0")
        assert response.status_code == 422


class TestSceneHighlightsCacheAndErrors:
    @patch(_VERSION, return_value="v1")
    @patch(_GW)
    @patch(_CACHE)
    def test_cache_hit_skips_gateway(self, mock_get_cache, mock_gw, _mock_ver):
        """A cache HIT returns the cached payload and never calls the gateway."""
        mock_get_cache.return_value = _hit_cache(
            {"window": "all", "sort": "hype", "items": [], "has_more": False}
        )

        response = TestClient(app).get("/scene/highlights")

        assert response.status_code == 200
        assert response.headers["X-Cache"] == "HIT"
        mock_gw.assert_not_called()

    @patch(_VERSION, return_value="v1")
    @patch(_GW)
    @patch(_CACHE)
    def test_gateway_error_is_500(self, mock_get_cache, mock_gw, _mock_ver):
        """A gateway error surfaces as a 500 via the error boundary."""
        mock_get_cache.return_value = _miss_cache()
        mock_gw.side_effect = Exception("boom")

        response = TestClient(app).get("/scene/highlights")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"
