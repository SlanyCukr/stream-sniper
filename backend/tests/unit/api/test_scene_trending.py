"""Unit tests for the scene-wide trending (velocity) endpoints.

GET /scene/trending/copypastas and GET /scene/trending/emotes.

Gateway functions are monkeypatched; the router is mounted on a fresh app. Response
shaping, trend classification, delta_pct, and validation are asserted here — the
FILTER-window SQL (incl. the current/prior boundary and the min-usage floor) is
verified against a scratch Postgres in the gateway verification step, not this suite.
"""

from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.error_boundary import UnexpectedExceptionMiddleware
from stream_sniper.api.features.content.scene_trending_endpoints import router
from stream_sniper.api.security.rate_limiter import setup_rate_limiting
from stream_sniper.database.gateways.analytics.scene_trends_gateway import (
    TrendingCopypastaRow,
    TrendingEmoteRow,
)


def _build_app():
    app = FastAPI()
    setup_rate_limiting(app)
    app.add_middleware(UnexpectedExceptionMiddleware)
    app.include_router(router)
    return app


app = _build_app()


def _miss_cache():
    cache = Mock()
    cache.generate_key = Mock(side_effect=lambda *a, **k: "key:" + ":".join(str(x) for x in a))
    cache.get = Mock(return_value=None)
    cache.set = Mock(return_value=True)
    cache.delete = Mock(return_value=True)
    return cache


def _copypasta(mtid=1, current=10, prior=5, first_seen="2026-07-15T10:00:00"):
    return TrendingCopypastaRow(
        message_text_id=mtid,
        text=f"copypasta {mtid}",
        current_usage=current,
        prior_usage=prior,
        stream_count=3,
        creator_count=2,
        first_seen=first_seen,
    )


def _emote(eid=1, current=10, prior=5, first_seen="2026-01-01T00:00:00"):
    return TrendingEmoteRow(
        emote_id=eid,
        name=f"Emote{eid}",
        source="bttv",
        provider_id="abc123",
        current_usage=current,
        prior_usage=prior,
        chatter_reach=7,
        first_seen=first_seen,
    )


class TestTrendingCopypastas:
    @patch("stream_sniper.api.features.content.scene_trending_endpoints.get_cache")
    @patch("stream_sniper.api.features.content.scene_trending_endpoints.scene_rollup_version")
    @patch("stream_sniper.api.features.content.scene_trending_endpoints.select_trending_copypastas_db")
    def test_shapes_item_and_defaults(self, mock_gw, mock_ver, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_ver.return_value = "v1"
        mock_gw.return_value = [_copypasta(1, current=10, prior=5)]

        with TestClient(app) as client:
            resp = client.get("/scene/trending/copypastas")

        assert resp.status_code == 200
        data = resp.json()
        assert data["window"] == 7
        assert len(data["items"]) == 1
        assert data["items"][0] == {
            "message_text_id": 1,
            "text": "copypasta 1",
            "current_usage": 10,
            "prior_usage": 5,
            "delta_pct": 100.0,
            "trend": "rising",
            "stream_count": 3,
            "creator_count": 2,
            "first_seen": "2026-07-15T10:00:00",
        }
        # default window=7, no creator filter, default limit=20
        mock_gw.assert_called_once_with(7, None, 20)

    @patch("stream_sniper.api.features.content.scene_trending_endpoints.get_cache")
    @patch("stream_sniper.api.features.content.scene_trending_endpoints.scene_rollup_version")
    @patch("stream_sniper.api.features.content.scene_trending_endpoints.select_trending_copypastas_db")
    def test_trend_classification_all_buckets(self, mock_gw, mock_ver, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_ver.return_value = "v1"
        mock_gw.return_value = [
            _copypasta(1, current=10, prior=0),  # new
            _copypasta(2, current=20, prior=10),  # rising
            _copypasta(3, current=5, prior=10),  # falling
            _copypasta(4, current=8, prior=8),  # steady
        ]

        with TestClient(app) as client:
            resp = client.get("/scene/trending/copypastas?window=14")

        assert resp.status_code == 200
        items = resp.json()["items"]
        by_id = {i["message_text_id"]: i for i in items}
        assert by_id[1]["trend"] == "new"
        assert by_id[1]["delta_pct"] is None
        assert by_id[2]["trend"] == "rising"
        assert by_id[2]["delta_pct"] == 100.0
        assert by_id[3]["trend"] == "falling"
        assert by_id[3]["delta_pct"] == -50.0
        assert by_id[4]["trend"] == "steady"
        assert by_id[4]["delta_pct"] == 0.0

    @patch("stream_sniper.api.features.content.scene_trending_endpoints.get_cache")
    @patch("stream_sniper.api.features.content.scene_trending_endpoints.scene_rollup_version")
    @patch("stream_sniper.api.features.content.scene_trending_endpoints.select_trending_copypastas_db")
    def test_forwards_creator_and_limit(self, mock_gw, mock_ver, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_ver.return_value = "v1"
        mock_gw.return_value = []

        with TestClient(app) as client:
            resp = client.get("/scene/trending/copypastas?window=30&creator_id=4&limit=5")

        assert resp.status_code == 200
        assert resp.json() == {"window": 30, "items": []}
        mock_gw.assert_called_once_with(30, 4, 5)

    @patch("stream_sniper.api.features.content.scene_trending_endpoints.get_cache")
    @patch("stream_sniper.api.features.content.scene_trending_endpoints.scene_rollup_version")
    @patch("stream_sniper.api.features.content.scene_trending_endpoints.select_trending_copypastas_db")
    def test_null_first_seen_survives(self, mock_gw, mock_ver, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_ver.return_value = "v1"
        mock_gw.return_value = [_copypasta(1, first_seen=None)]

        with TestClient(app) as client:
            resp = client.get("/scene/trending/copypastas")

        assert resp.status_code == 200
        assert resp.json()["items"][0]["first_seen"] is None

    def test_invalid_window_is_422(self):
        for window in (1, 10, 60, 0):
            with TestClient(app) as client:
                resp = client.get(f"/scene/trending/copypastas?window={window}")
            assert resp.status_code == 422
            assert "7, 14, or 30" in resp.json()["detail"]

    def test_limit_above_max_is_422(self):
        with TestClient(app) as client:
            resp = client.get("/scene/trending/copypastas?limit=51")
        assert resp.status_code == 422

    def test_limit_below_min_is_422(self):
        with TestClient(app) as client:
            resp = client.get("/scene/trending/copypastas?limit=0")
        assert resp.status_code == 422

    @patch("stream_sniper.api.features.content.scene_trending_endpoints.get_cache")
    @patch("stream_sniper.api.features.content.scene_trending_endpoints.scene_rollup_version")
    @patch("stream_sniper.api.features.content.scene_trending_endpoints.select_trending_copypastas_db")
    def test_gateway_error_returns_500(self, mock_gw, mock_ver, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_ver.return_value = "v1"
        mock_gw.side_effect = Exception("db down")

        with TestClient(app) as client:
            resp = client.get("/scene/trending/copypastas")

        assert resp.status_code == 500
        assert resp.json()["detail"] == "Internal server error"


class TestTrendingEmotes:
    @patch("stream_sniper.api.features.content.scene_trending_endpoints.get_cache")
    @patch("stream_sniper.api.features.content.scene_trending_endpoints.scene_rollup_version")
    @patch("stream_sniper.api.features.content.scene_trending_endpoints.select_trending_emotes_db")
    def test_shapes_item_and_defaults(self, mock_gw, mock_ver, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_ver.return_value = "v1"
        mock_gw.return_value = [_emote(1, current=30, prior=0)]

        with TestClient(app) as client:
            resp = client.get("/scene/trending/emotes")

        assert resp.status_code == 200
        data = resp.json()
        assert data["window"] == 7
        assert data["items"][0] == {
            "emote_id": 1,
            "name": "Emote1",
            "source": "bttv",
            "provider_id": "abc123",
            "current_usage": 30,
            "prior_usage": 0,
            "delta_pct": None,
            "trend": "new",
            "chatter_reach": 7,
            "first_seen": "2026-01-01T00:00:00",
        }
        mock_gw.assert_called_once_with(7, None, 20)

    @patch("stream_sniper.api.features.content.scene_trending_endpoints.get_cache")
    @patch("stream_sniper.api.features.content.scene_trending_endpoints.scene_rollup_version")
    @patch("stream_sniper.api.features.content.scene_trending_endpoints.select_trending_emotes_db")
    def test_trend_classification_all_buckets(self, mock_gw, mock_ver, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_ver.return_value = "v1"
        mock_gw.return_value = [
            _emote(1, current=10, prior=0),  # new
            _emote(2, current=20, prior=10),  # rising
            _emote(3, current=5, prior=10),  # falling
            _emote(4, current=8, prior=8),  # steady
        ]

        with TestClient(app) as client:
            resp = client.get("/scene/trending/emotes?window=14&creator_id=2&limit=10")

        assert resp.status_code == 200
        items = resp.json()["items"]
        by_id = {i["emote_id"]: i for i in items}
        assert (by_id[1]["trend"], by_id[1]["delta_pct"]) == ("new", None)
        assert (by_id[2]["trend"], by_id[2]["delta_pct"]) == ("rising", 100.0)
        assert (by_id[3]["trend"], by_id[3]["delta_pct"]) == ("falling", -50.0)
        assert (by_id[4]["trend"], by_id[4]["delta_pct"]) == ("steady", 0.0)
        mock_gw.assert_called_once_with(14, 2, 10)

    @patch("stream_sniper.api.features.content.scene_trending_endpoints.get_cache")
    @patch("stream_sniper.api.features.content.scene_trending_endpoints.scene_rollup_version")
    @patch("stream_sniper.api.features.content.scene_trending_endpoints.select_trending_emotes_db")
    def test_null_provider_and_first_seen(self, mock_gw, mock_ver, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_ver.return_value = "v1"
        row = _emote(1)._replace(provider_id=None, first_seen=None)
        mock_gw.return_value = [row]

        with TestClient(app) as client:
            resp = client.get("/scene/trending/emotes")

        assert resp.status_code == 200
        item = resp.json()["items"][0]
        assert item["provider_id"] is None
        assert item["first_seen"] is None

    def test_invalid_window_is_422(self):
        with TestClient(app) as client:
            resp = client.get("/scene/trending/emotes?window=3")
        assert resp.status_code == 422
        assert "7, 14, or 30" in resp.json()["detail"]

    def test_limit_above_max_is_422(self):
        with TestClient(app) as client:
            resp = client.get("/scene/trending/emotes?limit=100")
        assert resp.status_code == 422
