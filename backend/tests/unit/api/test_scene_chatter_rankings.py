"""Unit tests for the scene chatter power-rankings endpoint.

The scene-chatter router is mounted onto a dedicated test app with the real limiter,
and the rankings gateway is patched at the endpoint module's import path. Postgres is
never touched (real bot exclusion / window SQL is verified against a scratch DB). These
tests cover window handling, response shaping, pagination, and caching.
"""

from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.caching.cache import InProcessCache
from stream_sniper.api.error_boundary import UnexpectedExceptionMiddleware
from stream_sniper.api.features.content.scene_chatter_endpoints import router
from stream_sniper.api.security.rate_limiter import setup_rate_limiting
from stream_sniper.database.gateways.creators.scene_chatter_rankings_gateway import SceneChatterRankRow


def _build_app():
    app = FastAPI()
    setup_rate_limiting(app)
    app.add_middleware(UnexpectedExceptionMiddleware)
    app.include_router(router)
    return app


app = _build_app()


def _miss_cache():
    cache = Mock()
    cache.generate_key = Mock(side_effect=lambda *args: "-".join(str(a) for a in args))
    cache.get = Mock(return_value=None)
    cache.set = Mock(return_value=True)
    return cache


def _hit_cache(payload):
    cache = Mock()
    cache.generate_key = Mock(side_effect=lambda *args: "-".join(str(a) for a in args))
    cache.get = Mock(return_value=payload)
    cache.set = Mock(return_value=True)
    return cache


def _row(
    chatter_id,
    nick,
    total,
    streams,
    creators,
    *,
    home_id=5,
    home_msgs=None,
    first_seen=None,
    lifetime=None,
):
    """``lifetime`` overrides the account-wide archetype aggregates; by default they
    mirror the window aggregates (the all-time path's real behavior)."""
    home_messages = home_msgs if home_msgs is not None else total
    lifetime = lifetime or {}
    return SceneChatterRankRow(
        chatter_id=chatter_id,
        nick=nick,
        total_messages=total,
        streams_attended=streams,
        creators_visited=creators,
        first_seen=first_seen,
        home_creator_id=home_id,
        home_creator_nick="homie",
        home_creator_display_name="Homie",
        home_messages=home_messages,
        lifetime_messages=lifetime.get("messages", total),
        lifetime_streams=lifetime.get("streams", streams),
        lifetime_creators=lifetime.get("creators", creators),
        lifetime_home_messages=lifetime.get("home_messages", home_messages),
    )


_VERSION = "stream_sniper.api.features.content.scene_chatter_endpoints.scene_rollup_version"
_CACHE = "stream_sniper.api.features.content.scene_chatter_endpoints.get_cache"
_GATEWAY = "stream_sniper.api.features.content.scene_chatter_endpoints.select_scene_chatter_rankings_db"


class TestChatterRankingsEndpoint:
    @patch(_VERSION, return_value="v1")
    @patch(_CACHE)
    @patch(_GATEWAY)
    def test_default_window_all_shaping(self, mock_gw, mock_get_cache, _v):
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = (
            [
                _row(42, "chatty", 1000, 15, 2, home_id=5, home_msgs=800),
                _row(9, "wanderer", 400, 20, 8, home_id=7, home_msgs=100),
            ],
            False,
        )

        response = TestClient(app).get("/scene/chatter-rankings")

        assert response.status_code == 200
        assert response.headers["X-Cache"] == "MISS"
        data = response.json()
        assert data["window"] == "all"
        assert data["has_more"] is False
        assert [item["rank"] for item in data["items"]] == [1, 2]
        top = data["items"][0]
        assert top["chatter_id"] == 42
        assert top["nick"] == "chatty"
        assert top["total_messages"] == 1000
        assert top["streams_attended"] == 15
        assert top["creators_visited"] == 2
        assert top["home_channel"] == {
            "creator_id": 5,
            "creator_nick": "homie",
            "creator_display_name": "Homie",
            "messages": 800,
            "share": 0.8,
        }
        # all-time path -> gateway called with window_days=None
        mock_gw.assert_called_once_with(None, 50, 0)

    @patch(_VERSION, return_value="v1")
    @patch(_CACHE)
    @patch(_GATEWAY)
    def test_window_7_and_30_forwarded(self, mock_gw, mock_get_cache, _v):
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = ([], False)

        TestClient(app).get("/scene/chatter-rankings?window=7")
        mock_gw.assert_called_with(7, 50, 0)

        TestClient(app).get("/scene/chatter-rankings?window=30&limit=10&offset=5")
        mock_gw.assert_called_with(30, 10, 5)

    def test_invalid_window_422(self):
        response = TestClient(app).get("/scene/chatter-rankings?window=90")
        assert response.status_code == 422
        assert response.json()["detail"] == "window must be 'all', '7', or '30'."

    def test_limit_over_max_422(self):
        response = TestClient(app).get("/scene/chatter-rankings?limit=101")
        assert response.status_code == 422

    def test_negative_offset_422(self):
        response = TestClient(app).get("/scene/chatter-rankings?offset=-1")
        assert response.status_code == 422

    @patch(_VERSION, return_value="v1")
    @patch(_CACHE)
    @patch(_GATEWAY)
    def test_pagination_rank_is_offset_aware(self, mock_gw, mock_get_cache, _v):
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = ([_row(3, "c", 100, 2, 1), _row(4, "d", 90, 2, 1)], True)

        response = TestClient(app).get("/scene/chatter-rankings?offset=20&limit=2")

        assert response.status_code == 200
        data = response.json()
        assert data["has_more"] is True
        assert [item["rank"] for item in data["items"]] == [21, 22]

    @patch(_VERSION, return_value="v1")
    @patch(_CACHE)
    @patch(_GATEWAY)
    def test_null_home_channel_serializes(self, mock_gw, mock_get_cache, _v):
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = (
            [
                SceneChatterRankRow(
                    chatter_id=1,
                    nick="lonely",
                    total_messages=0,
                    streams_attended=0,
                    creators_visited=0,
                    first_seen=None,
                    home_creator_id=None,
                    home_creator_nick=None,
                    home_creator_display_name=None,
                    home_messages=None,
                    lifetime_messages=0,
                    lifetime_streams=0,
                    lifetime_creators=0,
                    lifetime_home_messages=None,
                )
            ],
            False,
        )

        response = TestClient(app).get("/scene/chatter-rankings")

        assert response.status_code == 200
        assert response.json()["items"][0]["home_channel"] is None

    @patch(_VERSION, return_value="v1")
    @patch(_CACHE)
    @patch(_GATEWAY)
    def test_empty_result(self, mock_gw, mock_get_cache, _v):
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = ([], False)

        response = TestClient(app).get("/scene/chatter-rankings?window=30")

        assert response.status_code == 200
        assert response.json() == {"window": "30", "items": [], "has_more": False}

    @patch(_VERSION, return_value="v1")
    @patch(_CACHE)
    @patch(_GATEWAY)
    def test_cache_hit_skips_gateway(self, mock_gw, mock_get_cache, _v):
        mock_get_cache.return_value = _hit_cache({"window": "all", "items": [], "has_more": False})

        response = TestClient(app).get("/scene/chatter-rankings")

        assert response.status_code == 200
        assert response.headers["X-Cache"] == "HIT"
        mock_gw.assert_not_called()

    @patch(_VERSION, return_value="v1")
    @patch(_CACHE)
    @patch(_GATEWAY)
    def test_cache_round_trip(self, mock_gw, mock_get_cache, _v):
        mock_get_cache.return_value = InProcessCache()
        mock_gw.return_value = ([_row(42, "chatty", 1000, 15, 2, home_msgs=800)], False)

        client = TestClient(app)
        first = client.get("/scene/chatter-rankings")
        second = client.get("/scene/chatter-rankings")

        assert first.json() == second.json()
        assert second.headers["X-Cache"] == "HIT"
        mock_gw.assert_called_once()

    @patch(_VERSION, return_value="v1")
    @patch(_CACHE)
    @patch(_GATEWAY)
    def test_gateway_error_is_500(self, mock_gw, mock_get_cache, _v):
        mock_get_cache.return_value = _miss_cache()
        mock_gw.side_effect = Exception("boom")

        response = TestClient(app).get("/scene/chatter-rankings")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"

    @patch(_VERSION, return_value="v1")
    @patch(_CACHE)
    @patch(_GATEWAY)
    def test_archetypes_present_for_crafted_row(self, mock_gw, mock_get_cache, _v):
        # home_share=5000/6000≈0.83 (>=0.70) with streams_attended=40 (>=3) -> loyalist.
        # 6000/40=150 msgs/stream (>=100) with streams_attended>=3 -> marathoner.
        # total_messages=6000 (>=5000) -> chatterbox.
        # first_seen far in the past (>180 days ago, always true) -> veteran.
        # creators_visited=2 (<5) -> not wanderer.
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = (
            [
                _row(
                    1,
                    "grinder",
                    6000,
                    40,
                    2,
                    home_msgs=5000,
                    first_seen="2020-01-01T00:00:00",
                )
            ],
            False,
        )

        response = TestClient(app).get("/scene/chatter-rankings")

        assert response.status_code == 200
        keys = [badge["key"] for badge in response.json()["items"][0]["archetypes"]]
        assert keys == ["loyalist", "marathoner", "chatterbox", "veteran"]

    @patch(_VERSION, return_value="v1")
    @patch(_CACHE)
    @patch(_GATEWAY)
    def test_archetypes_empty_without_home_channel(self, mock_gw, mock_get_cache, _v):
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = (
            [
                SceneChatterRankRow(
                    chatter_id=2,
                    nick="quiet",
                    total_messages=10,
                    streams_attended=1,
                    creators_visited=0,
                    first_seen=None,
                    home_creator_id=None,
                    home_creator_nick=None,
                    home_creator_display_name=None,
                    home_messages=None,
                    lifetime_messages=10,
                    lifetime_streams=1,
                    lifetime_creators=0,
                    lifetime_home_messages=None,
                )
            ],
            False,
        )

        response = TestClient(app).get("/scene/chatter-rankings")

        assert response.status_code == 200
        item = response.json()["items"][0]
        assert item["home_channel"] is None
        assert item["archetypes"] == []

    @patch(_VERSION, return_value="v1")
    @patch(_CACHE)
    @patch(_GATEWAY)
    def test_archetypes_use_lifetime_not_window_aggregates(self, mock_gw, mock_get_cache, _v):
        # In-window this chatter binged one channel (900/1000 = 0.90 share, which
        # would badge loyalist if the window slice fed the computation). Lifetime
        # they are the opposite: 10k messages spread over 8 creators with a top
        # channel at 3000/10000 = 0.30 -> wanderer (plus marathoner 10000/80=125,
        # chatterbox >= 5000, veteran). Badges must follow the lifetime identity.
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = (
            [
                _row(
                    7,
                    "binger",
                    1000,
                    5,
                    1,
                    home_msgs=900,
                    first_seen="2020-01-01T00:00:00",
                    lifetime={"messages": 10000, "streams": 80, "creators": 8, "home_messages": 3000},
                )
            ],
            False,
        )

        response = TestClient(app).get("/scene/chatter-rankings?window=7")

        assert response.status_code == 200
        item = response.json()["items"][0]
        # The displayed metrics stay window-scoped...
        assert item["total_messages"] == 1000
        assert item["home_channel"]["share"] == 0.9
        # ...but the badges are the account-wide identity.
        keys = [badge["key"] for badge in item["archetypes"]]
        assert keys == ["wanderer", "marathoner", "chatterbox", "veteran"]
        assert "loyalist" not in keys
