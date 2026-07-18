"""Unit tests for the Scene Wrapped recap endpoint (GET /scene/wrapped).

The recap's data-source gateways are monkeypatched at the application-assembly import
path (``wrapped_query``); the endpoint's cache and rollup-version probe are patched at the
endpoint path. Response shaping (ranks, peak-viewer merge, nullable passthrough, twitch_id
stringification, empty-scene zeros) and validation are asserted here — the two bespoke SQL
aggregates are verified against a scratch Postgres in the gateway step, not this suite.
"""

from contextlib import ExitStack
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.error_boundary import UnexpectedExceptionMiddleware
from stream_sniper.api.features.content.scene_wrapped_endpoints import router
from stream_sniper.api.security.rate_limiter import setup_rate_limiting
from stream_sniper.database.gateways.content.records import (
    SceneCopypastaRow,
    SceneEventRow,
    SceneLeaderboardRow,
    ScenePeakViewerRow,
)
from stream_sniper.database.gateways.content.scene_highlights_gateway import SceneHighlightRow
from stream_sniper.database.gateways.content.scene_wrapped_gateway import SceneWrappedEmoteRow
from stream_sniper.database.gateways.creators.scene_chatter_rankings_gateway import SceneChatterRankRow

_QUERY = "stream_sniper.application.scenes.wrapped_query"
_ENDPOINT = "stream_sniper.api.features.content.scene_wrapped_endpoints"


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


def _leaderboard_row(creator_id=1, streams=3, hours=6.0, messages=1000, mpm=12.5):
    return SceneLeaderboardRow(
        creator_id=creator_id,
        nick=f"creator{creator_id}",
        display_name=f"Creator {creator_id}",
        profile_image_url=f"http://img/{creator_id}.png",
        streams=streams,
        hours_streamed=hours,
        total_messages=messages,
        msgs_per_min=mpm,
        chatter_appearances=50,
    )


def _chatter_row(chatter_id=1, messages=500):
    return SceneChatterRankRow(
        chatter_id=chatter_id,
        nick=f"chatter{chatter_id}",
        total_messages=messages,
        streams_attended=4,
        creators_visited=2,
        first_seen=None,
        home_creator_id=1,
        home_creator_nick="creator1",
        home_creator_display_name="Creator 1",
        home_messages=300,
        lifetime_messages=messages,
        lifetime_streams=4,
        lifetime_creators=2,
        lifetime_home_messages=300,
    )


def _highlight_row(stream_id=1, twitch_id=99887766, ratio=4.2):
    return SceneHighlightRow(
        stream_id=stream_id,
        stream_title=f"Stream {stream_id}",
        twitch_id=twitch_id,
        creator_id=1,
        creator_nick="creator1",
        creator_display_name="Creator 1",
        bucket_minute="2026-07-17T20:15:00",
        offset_seconds=915,
        ratio=ratio,
        message_count=240,
        unique_chatters=120,
        sub_share=0.3,
        emote_share=0.6,
        top_phrases=None,
        sample_messages=None,
        clip_url=None,
        review_status=None,
    )


def _copypasta_row(mtid=1, usage=80):
    return SceneCopypastaRow(
        message_text_id=mtid,
        text=f"copypasta {mtid}",
        usage_count=usage,
        chatter_appearances=40,
        stream_count=5,
        creator_count=3,
        first_seen="2026-07-10T00:00:00",
        last_stream_start="2026-07-17T00:00:00",
    )


def _emote_row(emote_id=1, usage=500):
    return SceneWrappedEmoteRow(
        emote_id=emote_id,
        name=f"Emote{emote_id}",
        source="bttv",
        usage=usage,
        chatter_reach=90,
    )


def _event_row(event_id=1):
    return SceneEventRow(
        id=event_id,
        event_type="record_stream",
        occurred_at="2026-07-17T21:00:00",
        creator_id=1,
        creator_nick="creator1",
        creator_display_name="Creator 1",
        stream_id=1,
        message_text_id=None,
        title=f"Event {event_id}",
        summary="A notable thing happened",
        metadata=None,
    )


def _patch_query(
    *,
    leaderboard,
    peak,
    active_chatters,
    chatters,
    moments,
    copypastas,
    emotes,
    events,
):
    """Patch every gateway wrapped_query calls, plus the endpoint cache/version probe."""
    stack = ExitStack()
    stack.enter_context(patch(f"{_ENDPOINT}.get_cache", return_value=_miss_cache()))
    stack.enter_context(patch(f"{_ENDPOINT}.scene_rollup_version", return_value="v1"))
    stack.enter_context(patch(f"{_QUERY}.select_scene_leaderboard_db", return_value=leaderboard))
    stack.enter_context(patch(f"{_QUERY}.select_scene_peak_viewers_db", return_value=peak))
    stack.enter_context(patch(f"{_QUERY}.select_scene_active_chatters_db", return_value=active_chatters))
    stack.enter_context(patch(f"{_QUERY}.select_scene_chatter_rankings_db", return_value=(chatters, False)))
    stack.enter_context(patch(f"{_QUERY}.select_scene_highlights_db", return_value=(moments, False)))
    stack.enter_context(patch(f"{_QUERY}.select_scene_copypastas_db", return_value=(copypastas, len(copypastas))))
    stack.enter_context(patch(f"{_QUERY}.select_scene_emotes_db", return_value=emotes))
    stack.enter_context(patch(f"{_QUERY}.select_scene_events_db", return_value=(events, len(events))))
    return stack


class TestSceneWrapped:
    def test_full_recap_shape_and_defaults(self):
        leaderboard = [
            _leaderboard_row(1, streams=3, hours=6.0, messages=1000, mpm=12.5),
            _leaderboard_row(2, streams=2, hours=4.0, messages=800, mpm=None),
        ]
        with _patch_query(
            leaderboard=leaderboard,
            peak=[ScenePeakViewerRow(creator_id=1, peak_viewers=5000)],
            active_chatters=321,
            chatters=[_chatter_row(1, 500), _chatter_row(2, 400)],
            moments=[_highlight_row(1)],
            copypastas=[_copypasta_row(1)],
            emotes=[_emote_row(1)],
            events=[_event_row(1)],
        ):
            with TestClient(app) as client:
                resp = client.get("/scene/wrapped")

        assert resp.status_code == 200
        data = resp.json()
        assert data["days"] == 30  # default window
        assert data["totals"] == {
            "streams": 5,
            "hours_streamed": 10.0,
            "messages": 1800,
            "active_chatters": 321,
            "creators_active": 2,
        }
        # Top creators: 1-based rank, peak merged for creator 1, absent (null) for creator 2,
        # null msgs_per_min passed through (never coalesced to 0).
        assert data["top_creators"][0]["rank"] == 1
        assert data["top_creators"][0]["peak_viewers"] == 5000
        assert data["top_creators"][0]["msgs_per_min"] == 12.5
        assert data["top_creators"][1]["rank"] == 2
        assert data["top_creators"][1]["peak_viewers"] is None
        assert data["top_creators"][1]["msgs_per_min"] is None
        # Chatters ranked 1..n with home display name.
        assert [c["rank"] for c in data["top_chatters"]] == [1, 2]
        assert data["top_chatters"][0]["home_creator_display_name"] == "Creator 1"
        # Moment twitch_id rendered as a string.
        assert data["top_moments"][0]["twitch_id"] == "99887766"
        assert data["top_moments"][0]["ratio"] == 4.2
        # Copypasta / emote / event passthrough.
        assert data["top_copypastas"][0]["creator_count"] == 3
        assert data["top_emotes"][0]["usage"] == 500
        assert data["notable_events"][0]["creator_display_name"] == "Creator 1"

    def test_forwards_days_to_the_gateways(self):
        with _patch_query(
            leaderboard=[],
            peak=[],
            active_chatters=0,
            chatters=[],
            moments=[],
            copypastas=[],
            emotes=[],
            events=[],
        ) as stack:
            mock_lb = stack.enter_context(patch(f"{_QUERY}.select_scene_leaderboard_db", return_value=[]))
            mock_chatters = stack.enter_context(
                patch(f"{_QUERY}.select_scene_chatter_rankings_db", return_value=([], False))
            )
            mock_emotes = stack.enter_context(patch(f"{_QUERY}.select_scene_emotes_db", return_value=[]))
            with TestClient(app) as client:
                resp = client.get("/scene/wrapped?days=7")

        assert resp.status_code == 200
        mock_lb.assert_called_once_with(7)
        mock_chatters.assert_called_once_with(7, 5, 0)
        mock_emotes.assert_called_once_with(7, 5)

    def test_empty_scene_is_zeros_not_404(self):
        with _patch_query(
            leaderboard=[],
            peak=[],
            active_chatters=0,
            chatters=[],
            moments=[],
            copypastas=[],
            emotes=[],
            events=[],
        ):
            with TestClient(app) as client:
                resp = client.get("/scene/wrapped?days=14")

        assert resp.status_code == 200
        data = resp.json()
        assert data["totals"] == {
            "streams": 0,
            "hours_streamed": None,  # no streamed time -> unknown, not 0
            "messages": 0,
            "active_chatters": 0,
            "creators_active": 0,
        }
        assert data["top_creators"] == []
        assert data["top_chatters"] == []
        assert data["top_moments"] == []
        assert data["top_copypastas"] == []
        assert data["top_emotes"] == []
        assert data["notable_events"] == []

    def test_null_moment_twitch_id_and_ratio_survive(self):
        with _patch_query(
            leaderboard=[_leaderboard_row(1)],
            peak=[],
            active_chatters=1,
            chatters=[],
            moments=[_highlight_row(1, twitch_id=None, ratio=None)],
            copypastas=[],
            emotes=[],
            events=[],
        ):
            with TestClient(app) as client:
                resp = client.get("/scene/wrapped")

        assert resp.status_code == 200
        moment = resp.json()["top_moments"][0]
        assert moment["twitch_id"] is None
        assert moment["ratio"] is None

    def test_days_below_min_is_422(self):
        with TestClient(app) as client:
            resp = client.get("/scene/wrapped?days=6")
        assert resp.status_code == 422

    def test_days_above_max_is_422(self):
        with TestClient(app) as client:
            resp = client.get("/scene/wrapped?days=91")
        assert resp.status_code == 422

    def test_gateway_error_returns_500(self):
        with patch(f"{_ENDPOINT}.get_cache", return_value=_miss_cache()):
            with patch(f"{_ENDPOINT}.scene_rollup_version", return_value="v1"):
                with patch(f"{_QUERY}.select_scene_leaderboard_db", side_effect=Exception("db down")):
                    with TestClient(app) as client:
                        resp = client.get("/scene/wrapped")

        assert resp.status_code == 500
        assert resp.json()["detail"] == "Internal server error"
