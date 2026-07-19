"""Unit tests for the community-overlap endpoints (/community/*).

The community router is mounted on the shared app by the integration wiring step, so these
tests mount it on a minimal FastAPI app with the real rate limiter, patch the gateways by
their import path in ``community_endpoints``, and use an always-miss cache.
"""

from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.features.community.community_endpoints import router
from stream_sniper.api.security.rate_limiter import setup_rate_limiting
from stream_sniper.application.community.community_query import jaccard as _jaccard
from stream_sniper.database.gateways.community.records import (
    CommunityCreatorRow,
    CommunityPairRow,
    CreatorNeighborRow,
)


def _client() -> TestClient:
    app = FastAPI()
    setup_rate_limiting(app)
    app.include_router(router)
    return TestClient(app)


def _miss_cache():
    cache = Mock()
    cache.generate_key = Mock(return_value="test-cache-key")
    cache.get = Mock(return_value=None)
    cache.set = Mock(return_value=True)
    return cache


class TestJaccard:
    def test_normal_union(self):
        # shared 5, sizes 10 and 20 -> union 25 -> 0.2
        assert _jaccard(5, 10, 20) == 0.2

    def test_rounds_to_four_places(self):
        # shared 1, sizes 3 and 3 -> union 5 -> 0.2
        assert _jaccard(1, 3, 3) == 0.2
        # shared 1, sizes 2 and 2 -> union 3 -> 0.3333
        assert _jaccard(1, 2, 2) == 0.3333

    def test_zero_union_is_null(self):
        assert _jaccard(0, 0, 0) is None


class TestCommunityOverlapEndpoint:
    @patch("stream_sniper.api.features.community.community_endpoints.get_cache")
    @patch("stream_sniper.application.community.community_query.select_overlap_db")
    def test_success_maps_creators_pairs_and_jaccard(self, mock_overlap, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        creators = [
            CommunityCreatorRow(1, "alice", "Alice", 10, 4, "2024-01-15T20:00:00"),
            CommunityCreatorRow(2, "bob", "Bob", 20, 8, "2024-01-15T20:00:00"),
        ]
        pairs = [CommunityPairRow(1, 2, 5, 2)]
        mock_overlap.return_value = (creators, pairs)

        response = _client().get("/community/overlap?limit=40")

        assert response.status_code == 200
        data = response.json()
        assert data["computed_at"] == "2024-01-15T20:00:00"
        assert len(data["creators"]) == 2
        assert data["creators"][0] == {
            "creator_id": 1,
            "nick": "alice",
            "display_name": "Alice",
            "chatters": 10,
            "regulars": 4,
        }
        pair = data["pairs"][0]
        assert pair["a"] == 1 and pair["b"] == 2
        assert pair["shared_chatters"] == 5 and pair["shared_regulars"] == 2
        # chatters: 5 / (10 + 20 - 5) = 0.2 ; regulars: 2 / (4 + 8 - 2) = 0.2
        assert pair["jaccard_chatters"] == 0.2
        assert pair["jaccard_regulars"] == 0.2
        mock_overlap.assert_called_once_with(40)

    @patch("stream_sniper.api.features.community.community_endpoints.get_cache")
    @patch("stream_sniper.application.community.community_query.select_overlap_db")
    def test_zero_union_pair_yields_null_jaccard(self, mock_overlap, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        creators = [
            CommunityCreatorRow(3, "cara", "Cara", 0, 0, "2024-01-15T20:00:00"),
            CommunityCreatorRow(4, "dan", "Dan", 0, 0, "2024-01-15T20:00:00"),
        ]
        pairs = [CommunityPairRow(3, 4, 0, 0)]
        mock_overlap.return_value = (creators, pairs)

        response = _client().get("/community/overlap")

        assert response.status_code == 200
        pair = response.json()["pairs"][0]
        assert pair["jaccard_chatters"] is None
        assert pair["jaccard_regulars"] is None

    @patch("stream_sniper.api.features.community.community_endpoints.get_cache")
    @patch("stream_sniper.application.community.community_query.select_overlap_db")
    def test_empty_overlap_returns_null_computed_at(self, mock_overlap, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_overlap.return_value = ([], [])

        response = _client().get("/community/overlap")

        assert response.status_code == 200
        data = response.json()
        assert data["creators"] == []
        assert data["pairs"] == []
        assert data["computed_at"] is None

    def test_limit_over_max_rejected(self):
        response = _client().get("/community/overlap?limit=61")
        assert response.status_code == 422


class TestCreatorNeighborsEndpoint:
    @patch("stream_sniper.api.features.community.community_endpoints.get_cache")
    @patch("stream_sniper.application.community.community_query.select_creator_neighbors_db")
    def test_success_maps_metric_to_column(self, mock_neighbors, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_neighbors.return_value = [
            CreatorNeighborRow(8, "eve", "Eve", 12, 5),
            CreatorNeighborRow(9, "finn", "Finn", 7, 3),
        ]

        response = _client().get("/community/creators/5/neighbors?metric=regulars&limit=10")

        assert response.status_code == 200
        data = response.json()
        assert data["creator_id"] == 5
        assert data["metric"] == "regulars"
        assert data["neighbors"][0] == {
            "creator_id": 8,
            "nick": "eve",
            "display_name": "Eve",
            "shared_chatters": 12,
            "shared_regulars": 5,
        }
        # metric "regulars" maps to the whitelisted column "shared_regulars".
        mock_neighbors.assert_called_once_with(5, "shared_regulars", 10)

    @patch("stream_sniper.api.features.community.community_endpoints.get_cache")
    @patch("stream_sniper.application.community.community_query.select_creator_neighbors_db")
    def test_chatters_metric_maps_to_shared_chatters(self, mock_neighbors, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_neighbors.return_value = []

        response = _client().get("/community/creators/5/neighbors?metric=chatters")

        assert response.status_code == 200
        mock_neighbors.assert_called_once_with(5, "shared_chatters", 10)

    def test_invalid_metric_rejected(self):
        response = _client().get("/community/creators/5/neighbors?metric=bogus")
        assert response.status_code == 422


def _audience(cid, nick, chatters, regulars):
    return CommunityCreatorRow(cid, nick, nick.title(), chatters, regulars, "2026-07-19T06:00:00")


class TestHeadToHead:
    _Q = "stream_sniper.application.community.head_to_head_query"
    _E = "stream_sniper.api.features.community.community_endpoints"

    def _get(self, a, b):
        with (
            patch(f"{self._E}.get_cache", return_value=_miss_cache()),
            patch(f"{self._E}.scene_rollup_version", return_value="v1"),
        ):
            return _client().get(f"/community/head-to-head?creator_a={a}&creator_b={b}")

    def test_shapes_pair_with_shares_and_jaccard(self):
        with (
            patch(
                f"{self._Q}.select_creator_audiences_db",
                return_value=[_audience(3, "alpha", 100, 20), _audience(4, "beta", 50, 10)],
            ),
            patch(
                f"{self._Q}.select_creator_pair_overlap_db",
                return_value=CommunityPairRow(3, 4, 30, 5),
            ),
        ):
            response = self._get(3, 4)

        assert response.status_code == 200
        body = response.json()
        assert body["a"]["creator_id"] == 3
        assert body["a"]["shared_chatter_share"] == 0.3
        assert body["b"]["shared_chatter_share"] == 0.6
        assert body["shared_chatters"] == 30
        assert body["jaccard_chatters"] == _jaccard(30, 100, 50)
        assert body["computed_at"] == "2026-07-19T06:00:00"

    def test_param_order_never_changes_sides(self):
        with (
            patch(
                f"{self._Q}.select_creator_audiences_db",
                return_value=[_audience(3, "alpha", 100, 20), _audience(4, "beta", 50, 10)],
            ),
            patch(f"{self._Q}.select_creator_pair_overlap_db", return_value=None),
        ):
            response = self._get(4, 3)

        assert response.status_code == 200
        body = response.json()
        # Side `a` is always the lower creator id, regardless of param order.
        assert body["a"]["creator_id"] == 3
        assert body["shared_chatters"] == 0
        assert body["a"]["shared_chatter_share"] == 0.0

    def test_missing_audience_rollup_404s(self):
        with (
            patch(f"{self._Q}.select_creator_audiences_db", return_value=[_audience(3, "alpha", 100, 20)]),
            patch(f"{self._Q}.select_creator_pair_overlap_db", return_value=None),
        ):
            response = self._get(3, 99)

        assert response.status_code == 404

    def test_same_creator_rejected(self):
        response = self._get(5, 5)
        assert response.status_code == 400

    def test_empty_audience_share_is_null(self):
        with (
            patch(
                f"{self._Q}.select_creator_audiences_db",
                return_value=[_audience(3, "alpha", 0, 0), _audience(4, "beta", 50, 10)],
            ),
            patch(f"{self._Q}.select_creator_pair_overlap_db", return_value=None),
        ):
            response = self._get(3, 4)

        assert response.status_code == 200
        assert response.json()["a"]["shared_chatter_share"] is None
