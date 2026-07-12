"""Unit tests for per-stream/creator insight endpoints (mentions, emotes, phrases).

The insight router is mounted on a minimal FastAPI app with the real rate limiter; the
gateways are patched by their import path in ``stream_insight_endpoints`` and an
always-miss cache isolates each test from process-wide cache state.
"""

from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.rate_limiter import setup_rate_limiting
from stream_sniper.api.stream_insight_endpoints import router


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


class TestStreamMentions:
    @patch("stream_sniper.api.stream_insight_endpoints.get_cache")
    @patch("stream_sniper.api.stream_insight_endpoints.select_stream_mentions_db")
    def test_success_shape(self, mock_mentions, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mentioned = [(42, "target_a", 9), (43, "target_b", 4)]
        pairs = [(7, "caller", 42, "target_a", 5)]
        mock_mentions.return_value = (mentioned, pairs)

        response = _client().get("/stream/7/mentions")

        assert response.status_code == 200
        data = response.json()
        assert data["mentioned"] == [
            {"chatter_id": 42, "nick": "target_a", "count": 9},
            {"chatter_id": 43, "nick": "target_b", "count": 4},
        ]
        assert data["pairs"] == [
            {
                "from_chatter_id": 7,
                "from_nick": "caller",
                "to_chatter_id": 42,
                "to_nick": "target_a",
                "count": 5,
            }
        ]
        assert response.headers["X-Cache"] == "MISS"
        mock_mentions.assert_called_once_with(7, 20)

    @patch("stream_sniper.api.stream_insight_endpoints.get_cache")
    @patch("stream_sniper.api.stream_insight_endpoints.select_stream_mentions_db")
    def test_empty_returns_empty_lists(self, mock_mentions, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_mentions.return_value = ([], [])

        response = _client().get("/stream/7/mentions")

        assert response.status_code == 200
        assert response.json() == {"mentioned": [], "pairs": []}

    @patch("stream_sniper.api.stream_insight_endpoints.get_cache")
    @patch("stream_sniper.api.stream_insight_endpoints.select_stream_mentions_db")
    def test_custom_limit_forwarded(self, mock_mentions, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_mentions.return_value = ([], [])

        _client().get("/stream/7/mentions?limit=50")

        mock_mentions.assert_called_once_with(7, 50)

    def test_limit_below_min_rejected(self):
        assert _client().get("/stream/7/mentions?limit=0").status_code == 422

    def test_limit_above_max_rejected(self):
        assert _client().get("/stream/7/mentions?limit=101").status_code == 422

    @patch("stream_sniper.api.stream_insight_endpoints.get_cache")
    @patch("stream_sniper.api.stream_insight_endpoints.select_stream_mentions_db")
    def test_cache_hit_skips_gateway(self, mock_mentions, mock_get_cache):
        cache = Mock()
        cache._generate_key = Mock(return_value="k")
        cache.get = Mock(return_value={"mentioned": [], "pairs": []})
        cache.set = Mock()
        mock_get_cache.return_value = cache

        response = _client().get("/stream/7/mentions")

        assert response.status_code == 200
        assert response.headers["X-Cache"] == "HIT"
        mock_mentions.assert_not_called()


class TestStreamEmotes:
    @patch("stream_sniper.api.stream_insight_endpoints.get_cache")
    @patch("stream_sniper.api.stream_insight_endpoints.select_stream_emotes_db")
    def test_success_shape(self, mock_emotes, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_emotes.return_value = [
            ("KEKW", "bttv", "5e76d399d6581c3724c0f0b8", 120, 30),
            ("PogChamp", "twitch", "305954156", 40, 12),
        ]

        response = _client().get("/stream/7/emotes")

        assert response.status_code == 200
        data = response.json()
        assert data["emotes"][0] == {
            "name": "KEKW",
            "source": "bttv",
            "provider_id": "5e76d399d6581c3724c0f0b8",
            "usage_count": 120,
            "chatter_count": 30,
        }
        assert response.headers["X-Cache"] == "MISS"
        mock_emotes.assert_called_once_with(7, 25)

    @patch("stream_sniper.api.stream_insight_endpoints.get_cache")
    @patch("stream_sniper.api.stream_insight_endpoints.select_stream_emotes_db")
    def test_null_provider_id(self, mock_emotes, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_emotes.return_value = [("nopixel", "bttv", None, 5, 2)]

        data = _client().get("/stream/7/emotes").json()

        assert data["emotes"][0]["provider_id"] is None

    @patch("stream_sniper.api.stream_insight_endpoints.get_cache")
    @patch("stream_sniper.api.stream_insight_endpoints.select_stream_emotes_db")
    def test_empty_returns_empty_list(self, mock_emotes, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_emotes.return_value = []

        response = _client().get("/stream/7/emotes")

        assert response.status_code == 200
        assert response.json() == {"emotes": []}

    def test_limit_clamps(self):
        assert _client().get("/stream/7/emotes?limit=0").status_code == 422
        assert _client().get("/stream/7/emotes?limit=101").status_code == 422


class TestStreamPhrases:
    @patch("stream_sniper.api.stream_insight_endpoints.get_cache")
    @patch("stream_sniper.api.stream_insight_endpoints.select_stream_phrases_db")
    def test_success_shape(self, mock_phrases, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_phrases.return_value = [("gg wp", 22, 15), ("no way", 10, 8)]

        response = _client().get("/stream/7/phrases")

        assert response.status_code == 200
        data = response.json()
        assert data["phrases"][0] == {"phrase": "gg wp", "usage_count": 22, "chatter_count": 15}
        mock_phrases.assert_called_once_with(7, 25)

    @patch("stream_sniper.api.stream_insight_endpoints.get_cache")
    @patch("stream_sniper.api.stream_insight_endpoints.select_stream_phrases_db")
    def test_empty_returns_empty_list(self, mock_phrases, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_phrases.return_value = []

        response = _client().get("/stream/7/phrases")

        assert response.status_code == 200
        assert response.json() == {"phrases": []}

    def test_limit_clamps(self):
        assert _client().get("/stream/7/phrases?limit=0").status_code == 422
        assert _client().get("/stream/7/phrases?limit=101").status_code == 422


class TestCreatorEmotes:
    @patch("stream_sniper.api.stream_insight_endpoints.get_cache")
    @patch("stream_sniper.api.stream_insight_endpoints.select_creator_emotes_db")
    def test_success_shape_includes_stream_count(self, mock_emotes, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_emotes.return_value = [("KEKW", "bttv", "abc123def456", 500, 90, 12)]

        response = _client().get("/creator/3/emotes")

        assert response.status_code == 200
        data = response.json()
        assert data["emotes"][0] == {
            "name": "KEKW",
            "source": "bttv",
            "provider_id": "abc123def456",
            "usage_count": 500,
            "chatter_count": 90,
            "stream_count": 12,
        }
        mock_emotes.assert_called_once_with(3, 25)

    @patch("stream_sniper.api.stream_insight_endpoints.get_cache")
    @patch("stream_sniper.api.stream_insight_endpoints.select_creator_emotes_db")
    def test_empty_returns_empty_list(self, mock_emotes, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_emotes.return_value = []

        response = _client().get("/creator/3/emotes")

        assert response.status_code == 200
        assert response.json() == {"emotes": []}

    @patch("stream_sniper.api.stream_insight_endpoints.get_cache")
    @patch("stream_sniper.api.stream_insight_endpoints.select_creator_emotes_db")
    def test_cache_hit_skips_gateway(self, mock_emotes, mock_get_cache):
        cache = Mock()
        cache._generate_key = Mock(return_value="k")
        cache.get = Mock(return_value={"emotes": []})
        cache.set = Mock()
        mock_get_cache.return_value = cache

        response = _client().get("/creator/3/emotes")

        assert response.status_code == 200
        assert response.headers["X-Cache"] == "HIT"
        mock_emotes.assert_not_called()

    def test_limit_clamps(self):
        assert _client().get("/creator/3/emotes?limit=0").status_code == 422
        assert _client().get("/creator/3/emotes?limit=101").status_code == 422
