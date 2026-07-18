"""Unit tests for the Creator Wrapped recap endpoint (GET /creators/{creator_id}/wrapped).

The recap's data-source gateways are monkeypatched at the application-assembly import
path (``wrapped_query``); the endpoint's cache and rollup-version probe are patched at the
endpoint path. Mirrors ``test_scene_wrapped.py``'s style, plus the 404-on-unknown-creator
case shared with ``test_creator_analytics.py``'s summary suite.
"""

from contextlib import ExitStack
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.error_boundary import UnexpectedExceptionMiddleware
from stream_sniper.api.features.creators.creator_wrapped_endpoints import router
from stream_sniper.api.security.rate_limiter import setup_rate_limiting
from stream_sniper.database.gateways.content.records import SceneCopypastaRow
from stream_sniper.database.gateways.content.scene_highlights_gateway import SceneHighlightRow
from stream_sniper.database.gateways.content.scene_wrapped_gateway import SceneWrappedEmoteRow
from stream_sniper.database.gateways.creators.creator_wrapped_gateway import (
    CreatorWrappedChatterRow,
    CreatorWrappedTotalsRow,
)

_QUERY = "stream_sniper.application.creators.wrapped_query"
_ENDPOINT = "stream_sniper.api.features.creators.creator_wrapped_endpoints"


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


def _chatter_row(chatter_id=1, messages=500):
    return CreatorWrappedChatterRow(
        chatter_id=chatter_id,
        nick=f"chatter{chatter_id}",
        total_messages=messages,
        streams_attended=4,
    )


def _highlight_row(stream_id=1, twitch_id=99887766, ratio=4.2):
    return SceneHighlightRow(
        stream_id=stream_id,
        stream_title=f"Stream {stream_id}",
        twitch_id=twitch_id,
        creator_id=5,
        creator_nick="creator5",
        creator_display_name="Creator 5",
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
        creator_count=1,
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


def _patch_query(
    *,
    exists=True,
    totals=CreatorWrappedTotalsRow(0, None, 0),
    active_chatters=0,
    chatters=(),
    moments=(),
    copypastas=(),
    emotes=(),
):
    """Patch every gateway wrapped_query calls, plus the endpoint cache/version probe."""
    stack = ExitStack()
    stack.enter_context(patch(f"{_ENDPOINT}.get_cache", return_value=_miss_cache()))
    stack.enter_context(patch(f"{_ENDPOINT}.creator_rollup_version", return_value="v1"))
    stack.enter_context(patch(f"{_QUERY}.select_creator_exists_db", return_value=exists))
    stack.enter_context(patch(f"{_QUERY}.select_creator_wrapped_totals_db", return_value=totals))
    stack.enter_context(patch(f"{_QUERY}.select_creator_active_chatters_db", return_value=active_chatters))
    stack.enter_context(
        patch(f"{_QUERY}.select_creator_wrapped_chatters_db", return_value=(list(chatters), False))
    )
    stack.enter_context(patch(f"{_QUERY}.select_scene_highlights_db", return_value=(list(moments), False)))
    stack.enter_context(
        patch(f"{_QUERY}.select_scene_copypastas_db", return_value=(list(copypastas), len(copypastas)))
    )
    stack.enter_context(patch(f"{_QUERY}.select_creator_wrapped_emotes_db", return_value=list(emotes)))
    return stack


class TestCreatorWrapped:
    def test_full_recap_shape_and_defaults(self):
        with _patch_query(
            totals=CreatorWrappedTotalsRow(streams=3, hours_streamed=6.0, messages=1000),
            active_chatters=42,
            chatters=[_chatter_row(1, 500), _chatter_row(2, 400)],
            moments=[_highlight_row(1)],
            copypastas=[_copypasta_row(1)],
            emotes=[_emote_row(1)],
        ):
            with TestClient(app) as client:
                resp = client.get("/creators/5/wrapped")

        assert resp.status_code == 200
        data = resp.json()
        assert data["creator_id"] == 5
        assert data["days"] == 30  # default window
        assert data["totals"] == {
            "streams": 3,
            "hours_streamed": 6.0,
            "messages": 1000,
            "active_chatters": 42,
        }
        assert [c["rank"] for c in data["top_chatters"]] == [1, 2]
        assert data["top_chatters"][0]["chatter_id"] == 1
        assert data["top_moments"][0]["twitch_id"] == "99887766"
        assert data["top_moments"][0]["ratio"] == 4.2
        assert data["top_copypastas"][0]["stream_count"] == 5
        assert data["top_emotes"][0]["usage"] == 500

    def test_forwards_days_and_creator_id_to_the_gateways(self):
        with _patch_query() as stack:
            mock_totals = stack.enter_context(
                patch(
                    f"{_QUERY}.select_creator_wrapped_totals_db",
                    return_value=CreatorWrappedTotalsRow(0, None, 0),
                )
            )
            mock_chatters = stack.enter_context(
                patch(f"{_QUERY}.select_creator_wrapped_chatters_db", return_value=([], False))
            )
            with TestClient(app) as client:
                resp = client.get("/creators/5/wrapped?days=7")

        assert resp.status_code == 200
        mock_totals.assert_called_once_with(5, 7)
        mock_chatters.assert_called_once_with(5, 7, 5, 0)

    def test_empty_window_is_zeros_not_error(self):
        with _patch_query(totals=CreatorWrappedTotalsRow(0, None, 0)):
            with TestClient(app) as client:
                resp = client.get("/creators/5/wrapped?days=14")

        assert resp.status_code == 200
        data = resp.json()
        assert data["totals"] == {
            "streams": 0,
            "hours_streamed": None,  # no streamed time -> unknown, not 0
            "messages": 0,
            "active_chatters": 0,
        }
        assert data["top_chatters"] == []
        assert data["top_moments"] == []
        assert data["top_copypastas"] == []
        assert data["top_emotes"] == []

    def test_unknown_creator_404(self):
        with _patch_query(exists=False):
            with TestClient(app) as client:
                resp = client.get("/creators/404/wrapped")

        assert resp.status_code == 404
        assert resp.json()["detail"] == "Creator not found"

    def test_null_moment_twitch_id_and_ratio_survive(self):
        with _patch_query(moments=[_highlight_row(1, twitch_id=None, ratio=None)]):
            with TestClient(app) as client:
                resp = client.get("/creators/5/wrapped")

        assert resp.status_code == 200
        moment = resp.json()["top_moments"][0]
        assert moment["twitch_id"] is None
        assert moment["ratio"] is None

    def test_days_below_min_is_422(self):
        with TestClient(app) as client:
            resp = client.get("/creators/5/wrapped?days=6")
        assert resp.status_code == 422

    def test_days_above_max_is_422(self):
        with TestClient(app) as client:
            resp = client.get("/creators/5/wrapped?days=91")
        assert resp.status_code == 422

    def test_gateway_error_returns_500(self):
        with patch(f"{_ENDPOINT}.get_cache", return_value=_miss_cache()):
            with patch(f"{_ENDPOINT}.creator_rollup_version", return_value="v1"):
                with patch(f"{_QUERY}.select_creator_exists_db", side_effect=Exception("db down")):
                    with TestClient(app) as client:
                        resp = client.get("/creators/5/wrapped")

        assert resp.status_code == 500
        assert resp.json()["detail"] == "Internal server error"
