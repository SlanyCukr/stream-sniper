"""Unit tests for the chatter-passport endpoint (response shaping + 404).

The chatters router is mounted onto a dedicated test app; these tests exercise the
handler in isolation with a monkeypatched application query and an always-miss cache.
"""

from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.caching.cache import InProcessCache
from stream_sniper.api.error_boundary import UnexpectedExceptionMiddleware
from stream_sniper.api.features.chatters.chatter_endpoints import router
from stream_sniper.api.security.rate_limiter import setup_rate_limiting
from stream_sniper.application.chatters.passport_models import (
    ChatterPassport,
    PassportArchetype,
    PassportChatter,
    PassportCompanion,
    PassportDebut,
    PassportHomeChannel,
    PassportLoyalty,
    PassportMilestones,
    PassportMostActiveStream,
    PassportTotals,
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
    cache.generate_key = Mock(side_effect=lambda *args: "-".join(str(a) for a in args))
    cache.get = Mock(return_value=None)
    cache.set = Mock(return_value=True)
    return cache


def _sample_passport() -> ChatterPassport:
    return ChatterPassport(
        chatter=PassportChatter(id=42, nick="chatty", is_bot=False, bot_reason=None),
        totals=PassportTotals(
            messages=1000,
            streams_attended=15,
            creators_visited=2,
            first_seen="2024-01-01T00:00:00",
            last_seen="2024-06-01T00:00:00",
        ),
        debut=PassportDebut(
            stream_id=7, stream_title="First Stream", creator_display_name="Homie", time="2024-01-01T20:00:00"
        ),
        home_channel=PassportHomeChannel(
            creator_id=5, creator_nick="homie", creator_display_name="Homie", messages=800, share=0.8
        ),
        loyalty=[
            PassportLoyalty(
                creator_id=5,
                creator_nick="homie",
                creator_display_name="Homie",
                messages=800,
                streams_attended=12,
                share=0.8,
            ),
            PassportLoyalty(
                creator_id=9,
                creator_nick="other",
                creator_display_name="Other",
                messages=200,
                streams_attended=3,
                share=0.2,
            ),
        ],
        milestones=PassportMilestones(
            most_active_stream=PassportMostActiveStream(
                stream_id=11, title="Big One", creator_display_name="Homie", messages=350
            )
        ),
        archetypes=[
            PassportArchetype(key="loyalist", label="Loyalist", description="Devoted to one channel."),
        ],
        companions=[
            PassportCompanion(chatter_id=3, nick="buddy", shared_streams=9),
            PassportCompanion(chatter_id=8, nick="pal", shared_streams=4),
        ],
    )


class TestChatterPassportEndpoint:
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.scene_rollup_version", return_value="v1")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.query_chatter_passport")
    def test_passport_success_shape(self, mock_query, mock_get_cache, _mock_version):
        mock_get_cache.return_value = _miss_cache()
        mock_query.return_value = _sample_passport()

        with TestClient(app) as client:
            response = client.get("/chatters/42/passport")

        assert response.status_code == 200
        data = response.json()

        assert data["chatter"] == {"id": 42, "nick": "chatty", "is_bot": False, "bot_reason": None}
        assert data["totals"] == {
            "messages": 1000,
            "streams_attended": 15,
            "creators_visited": 2,
            "first_seen": "2024-01-01T00:00:00",
            "last_seen": "2024-06-01T00:00:00",
        }
        assert data["debut"]["stream_id"] == 7
        assert data["debut"]["time"] == "2024-01-01T20:00:00"
        assert data["home_channel"] == {
            "creator_id": 5,
            "creator_nick": "homie",
            "creator_display_name": "Homie",
            "messages": 800,
            "share": 0.8,
        }
        assert [entry["creator_id"] for entry in data["loyalty"]] == [5, 9]
        assert data["loyalty"][1]["share"] == 0.2
        assert data["milestones"]["most_active_stream"]["stream_id"] == 11
        assert data["milestones"]["most_active_stream"]["messages"] == 350
        assert data["archetypes"] == [
            {"key": "loyalist", "label": "Loyalist", "description": "Devoted to one channel."}
        ]
        assert data["companions"] == [
            {"chatter_id": 3, "nick": "buddy", "shared_streams": 9},
            {"chatter_id": 8, "nick": "pal", "shared_streams": 4},
        ]
        mock_query.assert_called_once_with(42)

    @patch("stream_sniper.api.features.chatters.chatter_endpoints.scene_rollup_version", return_value="v1")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.query_chatter_passport")
    def test_unknown_chatter_returns_404(self, mock_query, mock_get_cache, _mock_version):
        mock_get_cache.return_value = _miss_cache()
        mock_query.return_value = None

        with TestClient(app) as client:
            response = client.get("/chatters/999/passport")

        assert response.status_code == 404
        assert response.json()["detail"] == "Chatter not found"

    @patch("stream_sniper.api.features.chatters.chatter_endpoints.scene_rollup_version", return_value="v1")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.query_chatter_passport")
    def test_passport_null_optionals_serialize(self, mock_query, mock_get_cache, _mock_version):
        mock_get_cache.return_value = _miss_cache()
        mock_query.return_value = ChatterPassport(
            chatter=PassportChatter(id=1, nick="quiet", is_bot=None, bot_reason=None),
            totals=PassportTotals(
                messages=0, streams_attended=0, creators_visited=0, first_seen=None, last_seen=None
            ),
            debut=None,
            home_channel=None,
            loyalty=[],
            milestones=PassportMilestones(most_active_stream=None),
        )

        with TestClient(app) as client:
            response = client.get("/chatters/1/passport")

        assert response.status_code == 200
        data = response.json()
        assert data["debut"] is None
        assert data["home_channel"] is None
        assert data["loyalty"] == []
        assert data["milestones"]["most_active_stream"] is None
        assert data["chatter"]["is_bot"] is None
        # archetypes/companions default to an empty list when none are supplied
        assert data["archetypes"] == []
        assert data["companions"] == []

    @patch("stream_sniper.api.features.chatters.chatter_endpoints.scene_rollup_version", return_value="v1")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.get_cache")
    @patch("stream_sniper.api.features.chatters.chatter_endpoints.query_chatter_passport")
    def test_passport_survives_cache_round_trip(self, mock_query, mock_get_cache, _mock_version):
        cache = InProcessCache()
        mock_get_cache.return_value = cache
        mock_query.return_value = _sample_passport()

        with TestClient(app) as client:
            first = client.get("/chatters/42/passport")
            second = client.get("/chatters/42/passport")

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json() == second.json()
        assert second.headers["X-Cache"] == "HIT"
        # second request served from cache — query invoked only once
        mock_query.assert_called_once_with(42)
