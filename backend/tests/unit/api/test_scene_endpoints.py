"""Unit tests for the scene endpoints (live-now, leaderboard, copypasta library).

The scene router is mounted onto a dedicated test app with the real limiter, and every
gateway is patched at the endpoint module's import path. Postgres is never touched.
"""

from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.error_boundary import UnexpectedExceptionMiddleware
from stream_sniper.api.features.content.scene_endpoints import router
from stream_sniper.api.security.rate_limiter import setup_rate_limiting
from stream_sniper.database.gateways.content.records import (
    CopypastaContextRow,
    CopypastaOccurrenceRow,
    SceneCopypastaRow,
    SceneLeaderboardRow,
    ScenePeakViewerRow,
)
from stream_sniper.database.gateways.streams.records import LiveNowRow


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


class TestSceneLiveEndpoint:
    """GET /scene/live."""

    @patch("stream_sniper.api.features.content.scene_endpoints.get_cache")
    @patch("stream_sniper.application.scenes.scene_query.select_latest_sample_time_db")
    @patch("stream_sniper.application.scenes.scene_query.select_live_now_db")
    def test_live_sorted_by_viewer_count_desc(self, mock_live, mock_latest, mock_get_cache):
        """Live streamers are sorted by viewer_count DESC regardless of gateway order."""
        mock_get_cache.return_value = _miss_cache()
        mock_live.return_value = [
            LiveNowRow(1, "small", "Small", "http://a", 50, "hi", "2024-01-01T18:00:00", "2024-01-01T20:00:00"),
            LiveNowRow(2, "big", "Big", None, 5000, "yo", "2024-01-01T17:00:00", "2024-01-01T20:01:00"),
        ]
        mock_latest.return_value = "2024-01-01T20:01:00"

        response = TestClient(app).get("/scene/live")

        assert response.status_code == 200
        assert response.headers["X-Cache"] == "MISS"
        data = response.json()
        assert data["live_count"] == 2
        assert data["last_sample_at"] == "2024-01-01T20:01:00"
        assert [s["creator_id"] for s in data["live"]] == [2, 1]
        assert data["live"][0]["viewer_count"] == 5000
        assert data["live"][0]["profile_image_url"] is None

    @patch("stream_sniper.api.features.content.scene_endpoints.get_cache")
    @patch("stream_sniper.application.scenes.scene_query.select_latest_sample_time_db")
    @patch("stream_sniper.application.scenes.scene_query.select_live_now_db")
    def test_live_empty_returns_200(self, mock_live, mock_latest, mock_get_cache):
        """Nobody live is a valid 200 with an empty list and null last_sample_at."""
        mock_get_cache.return_value = _miss_cache()
        mock_live.return_value = []
        mock_latest.return_value = None

        response = TestClient(app).get("/scene/live")

        assert response.status_code == 200
        assert response.json() == {"live": [], "live_count": 0, "last_sample_at": None}

    @patch("stream_sniper.api.features.content.scene_endpoints.get_cache")
    @patch("stream_sniper.application.scenes.scene_query.select_live_now_db")
    def test_live_cache_hit_skips_gateway(self, mock_live, mock_get_cache):
        """A cache HIT returns the cached payload and never calls the gateway."""
        mock_get_cache.return_value = _hit_cache({"live": [], "live_count": 0, "last_sample_at": None})

        response = TestClient(app).get("/scene/live")

        assert response.status_code == 200
        assert response.headers["X-Cache"] == "HIT"
        mock_live.assert_not_called()

    @patch("stream_sniper.api.features.content.scene_endpoints.get_cache")
    @patch("stream_sniper.application.scenes.scene_query.select_latest_sample_time_db")
    @patch("stream_sniper.application.scenes.scene_query.select_live_now_db")
    def test_live_server_error(self, mock_live, mock_latest, mock_get_cache):
        """A gateway error surfaces as a 500."""
        mock_get_cache.return_value = _miss_cache()
        mock_live.side_effect = Exception("boom")

        response = TestClient(app).get("/scene/live")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"


class TestSceneLeaderboardEndpoint:
    """GET /scene/leaderboard."""

    @patch("stream_sniper.api.features.content.scene_endpoints.get_cache")
    @patch("stream_sniper.application.scenes.scene_query.select_scene_peak_viewers_db")
    @patch("stream_sniper.application.scenes.scene_query.select_scene_leaderboard_db")
    def test_leaderboard_rank_and_nulls(self, mock_board, mock_peak, mock_get_cache):
        """Rank is assigned in order; missing msgs_per_min / peak_viewers stay null."""
        mock_get_cache.return_value = _miss_cache()
        mock_board.return_value = [
            SceneLeaderboardRow(5, "top", "Top", "http://a", 10, 42.5, 100000, 33.3, 900),
            SceneLeaderboardRow(8, "second", "Second", None, 4, 2.0, 5000, None, 120),
        ]
        mock_peak.return_value = [ScenePeakViewerRow(5, 8000)]

        response = TestClient(app).get("/scene/leaderboard?window=30")

        assert response.status_code == 200
        data = response.json()
        assert data["window_days"] == 30
        assert data["entries"][0]["rank"] == 1
        assert data["entries"][0]["creator_id"] == 5
        assert data["entries"][0]["peak_viewers"] == 8000
        assert data["entries"][0]["msgs_per_min"] == 33.3
        assert data["entries"][1]["rank"] == 2
        assert data["entries"][1]["msgs_per_min"] is None
        assert data["entries"][1]["peak_viewers"] is None
        mock_board.assert_called_once_with(30)
        mock_peak.assert_called_once_with(30)

    @patch("stream_sniper.api.features.content.scene_endpoints.get_cache")
    @patch("stream_sniper.application.scenes.scene_query.select_scene_peak_viewers_db")
    @patch("stream_sniper.application.scenes.scene_query.select_scene_leaderboard_db")
    def test_leaderboard_default_window_7(self, mock_board, mock_peak, mock_get_cache):
        """The default window is 7 days."""
        mock_get_cache.return_value = _miss_cache()
        mock_board.return_value = []
        mock_peak.return_value = []

        response = TestClient(app).get("/scene/leaderboard")

        assert response.status_code == 200
        assert response.json() == {"window_days": 7, "entries": []}
        mock_board.assert_called_once_with(7)

    def test_leaderboard_invalid_window_422(self):
        """A window other than 7 or 30 is rejected before the gateway."""
        response = TestClient(app).get("/scene/leaderboard?window=5")
        assert response.status_code == 422

    @patch("stream_sniper.api.features.content.scene_endpoints.get_cache")
    @patch("stream_sniper.application.scenes.scene_query.select_scene_leaderboard_db")
    def test_leaderboard_cache_hit(self, mock_board, mock_get_cache):
        """A cache HIT skips the gateway."""
        mock_get_cache.return_value = _hit_cache({"window_days": 7, "entries": []})

        response = TestClient(app).get("/scene/leaderboard")

        assert response.status_code == 200
        assert response.headers["X-Cache"] == "HIT"
        mock_board.assert_not_called()

    @patch("stream_sniper.api.features.content.scene_endpoints.get_cache")
    @patch("stream_sniper.application.scenes.scene_query.select_scene_peak_viewers_db")
    @patch("stream_sniper.application.scenes.scene_query.select_scene_leaderboard_db")
    def test_leaderboard_server_error(self, mock_board, mock_peak, mock_get_cache):
        """A gateway error surfaces as a 500."""
        mock_get_cache.return_value = _miss_cache()
        mock_board.side_effect = Exception("boom")

        response = TestClient(app).get("/scene/leaderboard")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"


class TestSceneCopypastasEndpoint:
    """GET /scene/copypastas."""

    @patch("stream_sniper.api.features.content.scene_endpoints.get_cache")
    @patch("stream_sniper.application.scenes.scene_query.select_scene_copypastas_db")
    def test_copypastas_success_shape(self, mock_gw, mock_get_cache):
        """Rows map to the Copypasta contract and total is echoed."""
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = (
            [
                SceneCopypastaRow(
                    7,
                    "same message every time",
                    120,
                    45,
                    9,
                    4,
                    "2024-01-01T20:00:00",
                    "2024-02-01T20:00:00",
                ),
            ],
            1,
        )

        response = TestClient(app).get("/scene/copypastas")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        item = data["items"][0]
        assert item["message_text_id"] == 7
        assert item["text"] == "same message every time"
        assert item["usage_count"] == 120
        assert item["creator_count"] == 4
        # default: days=None, creator_id=None, sort=usage, limit=25, offset=0
        mock_gw.assert_called_once_with(None, None, "usage", 25, 0)

    @patch("stream_sniper.api.features.content.scene_endpoints.get_cache")
    @patch("stream_sniper.application.scenes.scene_query.select_scene_copypastas_db")
    def test_copypastas_empty_returns_200(self, mock_gw, mock_get_cache):
        """An empty rollup table yields 200 with total 0 and no items."""
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = ([], 0)

        response = TestClient(app).get("/scene/copypastas")

        assert response.status_code == 200
        assert response.json() == {"total": 0, "offset": 0, "limit": 25, "items": []}

    @patch("stream_sniper.api.features.content.scene_endpoints.get_cache")
    @patch("stream_sniper.application.scenes.scene_query.select_scene_copypastas_db")
    def test_copypastas_filters_forwarded(self, mock_gw, mock_get_cache):
        """days / creator_id / sort / limit / offset are forwarded to the gateway."""
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = ([], 0)

        response = TestClient(app).get("/scene/copypastas?days=30&creator_id=5&sort=spread&limit=10&offset=20")

        assert response.status_code == 200
        mock_gw.assert_called_once_with(30, 5, "spread", 10, 20)

    def test_copypastas_bad_sort_422(self):
        """A sort outside the whitelist is rejected before the gateway."""
        response = TestClient(app).get("/scene/copypastas?sort=bogus")
        assert response.status_code == 422

    def test_copypastas_limit_over_max_422(self):
        """limit above 100 is rejected."""
        response = TestClient(app).get("/scene/copypastas?limit=101")
        assert response.status_code == 422

    @patch("stream_sniper.api.features.content.scene_endpoints.get_cache")
    @patch("stream_sniper.application.scenes.scene_query.select_scene_copypastas_db")
    def test_copypastas_cache_hit(self, mock_gw, mock_get_cache):
        """A cache HIT skips the gateway."""
        mock_get_cache.return_value = _hit_cache({"total": 0, "offset": 0, "limit": 25, "items": []})

        response = TestClient(app).get("/scene/copypastas")

        assert response.status_code == 200
        assert response.headers["X-Cache"] == "HIT"
        mock_gw.assert_not_called()

    @patch("stream_sniper.api.features.content.scene_endpoints.get_cache")
    @patch("stream_sniper.application.scenes.scene_query.select_scene_copypastas_db")
    def test_copypastas_server_error(self, mock_gw, mock_get_cache):
        """A gateway error surfaces as a 500."""
        mock_get_cache.return_value = _miss_cache()
        mock_gw.side_effect = Exception("boom")

        response = TestClient(app).get("/scene/copypastas")

        assert response.status_code == 500
        assert response.json()["detail"] == "Internal server error"


class TestCopypastaPropagationEndpoint:
    """GET /scene/copypastas/{message_text_id}."""

    @patch("stream_sniper.api.features.content.scene_endpoints.get_cache")
    @patch("stream_sniper.application.scenes.scene_query.select_copypasta_context_db")
    @patch("stream_sniper.application.scenes.scene_query.select_copypasta_propagation_db")
    def test_propagation_maps_occurrences_and_origin_context(self, mock_propagation, mock_context, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_propagation.return_value = (
            "a legendary pasta",
            [
                CopypastaOccurrenceRow(
                    1,
                    5,
                    "alice",
                    "Alice",
                    None,
                    "Origin",
                    "2024-01-01T20:00:00",
                    "2024-01-01T20:05:00",
                    3,
                    2,
                ),
                CopypastaOccurrenceRow(
                    2,
                    6,
                    "bob",
                    "Bob",
                    None,
                    "Spread",
                    "2024-01-02T20:00:00",
                    "2024-01-02T20:06:00",
                    7,
                    4,
                ),
            ],
        )
        mock_context.return_value = [
            CopypastaContextRow(10, "2024-01-01T20:04:59.000000", 9, "viewer", "what happened"),
            CopypastaContextRow(11, "2024-01-01T20:05:00.000000", 10, "starter", "a legendary pasta"),
        ]

        response = TestClient(app).get("/scene/copypastas/42?context_seconds=120")

        assert response.status_code == 200
        data = response.json()
        assert data["message_text_id"] == 42
        assert data["usage_count"] == 10
        assert data["chatter_appearances"] == 6
        assert data["stream_count"] == 2
        assert data["creator_count"] == 2
        assert data["first_seen"] == "2024-01-01T20:05:00"
        assert data["occurrences"][1]["creator_id"] == 6
        assert data["origin_context"][1]["text"] == "a legendary pasta"
        mock_context.assert_called_once_with(1, "2024-01-01T20:05:00", 120, 100)

    @patch("stream_sniper.api.features.content.scene_endpoints.get_cache")
    @patch("stream_sniper.application.scenes.scene_query.select_copypasta_propagation_db")
    def test_missing_text_404(self, mock_propagation, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_propagation.return_value = (None, [])

        response = TestClient(app).get("/scene/copypastas/404")

        assert response.status_code == 404
        assert response.json()["detail"] == "Copypasta not found"

    def test_context_window_is_bounded(self):
        response = TestClient(app).get("/scene/copypastas/42?context_seconds=301")
        assert response.status_code == 422
