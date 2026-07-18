"""Unit tests for the scene-wide chat search endpoints (GET /search/*).

Gateway functions are monkeypatched; the router is mounted on a fresh app (the
api.py mount is a separate wave). Response shaping, validation, and wiring are
asserted here — the gateway SQL itself is smoke-tested against a scratch Postgres
in the migration/gateway verification step, not in this suite.
"""

from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.error_boundary import UnexpectedExceptionMiddleware
from stream_sniper.api.features.search.search_endpoints import router
from stream_sniper.api.security.rate_limiter import setup_rate_limiting
from stream_sniper.database.gateways.chat.message_replay_gateway import StreamContextRow
from stream_sniper.database.gateways.chat.message_search_gateway import (
    FirstMatchResult,
    SearchHitRow,
)
from stream_sniper.database.gateways.chat.records import MessageReplayRow


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


def _hit(message_id=1, time="2026-07-01T10:05:00.000000", creator=("alpha", "Alpha", 1)):
    nick, display, cid = creator
    return SearchHitRow(
        message_id=message_id,
        time=time,
        chatter_id=7,
        chatter_nick="usr7",
        chatter_is_bot=None,
        stream_id=3,
        stream_title="Some Stream",
        creator_id=cid,
        creator_nick=nick,
        creator_display_name=display,
        text="hello pog",
    )


class TestSearchMessages:
    @patch("stream_sniper.api.features.search.search_endpoints.get_cache")
    @patch("stream_sniper.api.features.search.search_endpoints.search_messages_db")
    def test_shapes_hits_and_has_more(self, mock_search, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_search.return_value = ([_hit(1), _hit(2)], True)

        with TestClient(app) as client:
            resp = client.get("/search/messages?q=pog")

        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "pog"
        assert data["has_more"] is True
        assert len(data["items"]) == 2
        assert data["items"][0] == {
            "message_id": 1,
            "time": "2026-07-01T10:05:00.000000",
            "text": "hello pog",
            "chatter": {"id": 7, "nick": "usr7", "is_bot": None},
            "stream": {"id": 3, "title": "Some Stream"},
            "creator": {"id": 1, "nick": "alpha", "display_name": "Alpha"},
        }
        mock_search.assert_called_once_with("pog", None, None, 50, 0)

    @patch("stream_sniper.api.features.search.search_endpoints.get_cache")
    @patch("stream_sniper.api.features.search.search_endpoints.search_messages_db")
    def test_forwards_filters_and_pagination(self, mock_search, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_search.return_value = ([], False)

        with TestClient(app) as client:
            resp = client.get("/search/messages?q=+ggg+&creator_id=4&days=30&limit=10&offset=20")

        assert resp.status_code == 200
        # query is stripped before hitting the gateway
        mock_search.assert_called_once_with("ggg", 4, 30, 10, 20)
        assert resp.json()["query"] == "ggg"

    def test_short_query_is_422(self):
        # 2 chars is below the floor too: pg_trgm cannot index-serve <3-char terms.
        for term in ("a", "ab"):
            with TestClient(app) as client:
                resp = client.get(f"/search/messages?q={term}")
            assert resp.status_code == 422
            assert "at least 3" in resp.json()["detail"]

    def test_whitespace_only_query_is_422(self):
        with TestClient(app) as client:
            resp = client.get("/search/messages?q=+++")
        assert resp.status_code == 422

    def test_too_long_query_is_422(self):
        with TestClient(app) as client:
            resp = client.get("/search/messages?q=" + "x" * 201)
        assert resp.status_code == 422

    def test_limit_above_max_is_422(self):
        with TestClient(app) as client:
            resp = client.get("/search/messages?q=pog&limit=101")
        assert resp.status_code == 422

    @patch("stream_sniper.api.features.search.search_endpoints.get_cache")
    @patch("stream_sniper.api.features.search.search_endpoints.search_messages_db")
    def test_gateway_error_returns_500(self, mock_search, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_search.side_effect = Exception("db down")

        with TestClient(app) as client:
            resp = client.get("/search/messages?q=pog")

        assert resp.status_code == 500
        assert resp.json()["detail"] == "Internal server error"


class TestSearchFirst:
    @patch("stream_sniper.api.features.search.search_endpoints.get_cache")
    @patch("stream_sniper.api.features.search.search_endpoints.select_first_messages_db")
    def test_shapes_first_by_creator_and_total(self, mock_first, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_first.return_value = FirstMatchResult(
            first=_hit(1, "2026-07-01T10:05:00.000000", ("alpha", "Alpha", 1)),
            by_creator=[
                _hit(1, "2026-07-01T10:05:00.000000", ("alpha", "Alpha", 1)),
                _hit(3, "2026-07-10T10:05:00.000000", ("beta", "Beta", 2)),
            ],
            total_matches=3,
        )

        with TestClient(app) as client:
            resp = client.get("/search/first?q=cafe")

        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "cafe"
        assert data["first"]["message_id"] == 1
        assert [h["creator"]["nick"] for h in data["by_creator"]] == ["alpha", "beta"]
        assert data["total_matches"] == 3
        mock_first.assert_called_once_with("cafe", None)

    @patch("stream_sniper.api.features.search.search_endpoints.get_cache")
    @patch("stream_sniper.api.features.search.search_endpoints.select_first_messages_db")
    def test_no_matches_returns_null_first(self, mock_first, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_first.return_value = FirstMatchResult(first=None, by_creator=[], total_matches=0)

        with TestClient(app) as client:
            resp = client.get("/search/first?q=zzz&creator_id=9")

        assert resp.status_code == 200
        data = resp.json()
        assert data["first"] is None
        assert data["by_creator"] == []
        assert data["total_matches"] == 0
        mock_first.assert_called_once_with("zzz", 9)


class TestSearchFrequency:
    @patch("stream_sniper.api.features.search.search_endpoints.get_cache")
    @patch("stream_sniper.api.features.search.search_endpoints.select_term_frequency_db")
    def test_zero_fills_continuous_window(self, mock_freq, mock_get_cache):
        from datetime import UTC, datetime, timedelta

        from stream_sniper.database.gateways.chat.message_search_gateway import TermFrequencyRow

        today = datetime.now(UTC).date()
        today_iso = today.isoformat()
        two_ago_iso = (today - timedelta(days=2)).isoformat()  # inside a 5-day window
        one_ago_iso = (today - timedelta(days=1)).isoformat()  # gateway returns no row here

        mock_get_cache.return_value = _miss_cache()
        mock_freq.return_value = [TermFrequencyRow(two_ago_iso, 2), TermFrequencyRow(today_iso, 4)]

        with TestClient(app) as client:
            resp = client.get("/search/frequency?q=ggg&days=5")

        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "ggg"
        assert data["days"] == 5
        # 5 continuous days, oldest first, gaps zero-filled
        assert len(data["points"]) == 5
        dates = [p["date"] for p in data["points"]]
        assert dates == sorted(dates)
        assert dates[-1] == today_iso
        counts_by_date = {p["date"]: p["count"] for p in data["points"]}
        assert counts_by_date[two_ago_iso] == 2
        assert counts_by_date[today_iso] == 4
        # a day with no gateway row is present with count 0
        assert counts_by_date[one_ago_iso] == 0
        mock_freq.assert_called_once_with("ggg", 5, None)

    def test_days_above_max_is_422(self):
        with TestClient(app) as client:
            resp = client.get("/search/frequency?q=ggg&days=366")
        assert resp.status_code == 422

    @patch("stream_sniper.api.features.search.search_endpoints.get_cache")
    @patch("stream_sniper.api.features.search.search_endpoints.select_term_frequency_db")
    def test_default_days_is_90(self, mock_freq, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_freq.return_value = []

        with TestClient(app) as client:
            resp = client.get("/search/frequency?q=ggg")

        assert resp.status_code == 200
        assert resp.json()["days"] == 90
        assert len(resp.json()["points"]) == 90
        mock_freq.assert_called_once_with("ggg", 90, None)


class TestSearchContext:
    @patch("stream_sniper.api.features.search.search_endpoints.get_cache")
    @patch("stream_sniper.api.features.search.search_endpoints.select_stream_context_db")
    @patch("stream_sniper.api.features.search.search_endpoints.select_message_window_db")
    def test_shapes_window_and_hit_index(self, mock_window, mock_ctx, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_window.return_value = [
            MessageReplayRow(3, "2026-07-10T10:05:00", 1, "botty", "CAFE time", None, None),
            MessageReplayRow(4, "2026-07-10T10:07:00", 2, "usr1", "Cafe great", True, "subscriber/1"),
            MessageReplayRow(5, "2026-07-10T10:08:00", 3, "usr2", "100% pog", None, None),
        ]
        mock_ctx.return_value = StreamContextRow(2, "Beta Stream", 2, "beta", "Beta")

        with TestClient(app) as client:
            resp = client.get("/search/context?stream_id=2&message_id=4&radius=1")

        assert resp.status_code == 200
        data = resp.json()
        assert data["stream"] == {
            "id": 2,
            "title": "Beta Stream",
            "creator": {"id": 2, "nick": "beta", "display_name": "Beta"},
        }
        assert [m["id"] for m in data["messages"]] == [3, 4, 5]
        assert data["hit_index"] == 1
        # replay-shaped: badges split into a list
        assert data["messages"][1]["badges"] == ["subscriber/1"]
        assert data["messages"][0]["badges"] == []
        mock_window.assert_called_once_with(2, 4, 1)

    @patch("stream_sniper.api.features.search.search_endpoints.get_cache")
    @patch("stream_sniper.api.features.search.search_endpoints.select_stream_context_db")
    @patch("stream_sniper.api.features.search.search_endpoints.select_message_window_db")
    def test_empty_window_is_404(self, mock_window, mock_ctx, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_window.return_value = []
        mock_ctx.return_value = StreamContextRow(2, "Beta Stream", 2, "beta", "Beta")

        with TestClient(app) as client:
            resp = client.get("/search/context?stream_id=2&message_id=999")

        assert resp.status_code == 404

    @patch("stream_sniper.api.features.search.search_endpoints.get_cache")
    @patch("stream_sniper.api.features.search.search_endpoints.select_stream_context_db")
    @patch("stream_sniper.api.features.search.search_endpoints.select_message_window_db")
    def test_hit_not_in_window_is_404(self, mock_window, mock_ctx, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        # window returned rows but none match the requested id
        mock_window.return_value = [
            MessageReplayRow(3, "2026-07-10T10:05:00", 1, "botty", "x", None, None),
        ]
        mock_ctx.return_value = StreamContextRow(2, "Beta Stream", 2, "beta", "Beta")

        with TestClient(app) as client:
            resp = client.get("/search/context?stream_id=2&message_id=4")

        assert resp.status_code == 404

    def test_radius_above_max_is_422(self):
        with TestClient(app) as client:
            resp = client.get("/search/context?stream_id=2&message_id=4&radius=101")
        assert resp.status_code == 422
