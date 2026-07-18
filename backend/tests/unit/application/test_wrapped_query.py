"""Unit tests for the Scene Wrapped assembly (get_scene_wrapped).

Gateways are monkeypatched at the ``wrapped_query`` import path; this suite asserts the
FastAPI-free assembly directly (peak-viewer merge, totals aggregation, hours-unknown on an
empty scene, top-N truncation and 1-based ranking).
"""

from contextlib import ExitStack
from unittest.mock import patch

from stream_sniper.application.scenes.wrapped_query import get_scene_wrapped
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


def _lb(creator_id, streams, hours, messages):
    return SceneLeaderboardRow(
        creator_id=creator_id,
        nick=f"c{creator_id}",
        display_name=f"C{creator_id}",
        profile_image_url=None,
        streams=streams,
        hours_streamed=hours,
        total_messages=messages,
        msgs_per_min=None,
        chatter_appearances=0,
    )


def _chatter(chatter_id):
    return SceneChatterRankRow(
        chatter_id=chatter_id,
        nick=f"ch{chatter_id}",
        total_messages=100,
        streams_attended=2,
        creators_visited=1,
        first_seen=None,
        home_creator_id=1,
        home_creator_nick="c1",
        home_creator_display_name="C1",
        home_messages=50,
        lifetime_messages=100,
        lifetime_streams=2,
        lifetime_creators=1,
        lifetime_home_messages=50,
    )


def _highlight():
    return SceneHighlightRow(
        stream_id=1,
        stream_title="S1",
        twitch_id=42,
        creator_id=1,
        creator_nick="c1",
        creator_display_name="C1",
        bucket_minute="2026-07-17T20:00:00",
        offset_seconds=10,
        ratio=3.0,
        message_count=100,
        unique_chatters=40,
        sub_share=None,
        emote_share=None,
        top_phrases=None,
        sample_messages=None,
        clip_url=None,
        review_status=None,
    )


def _copypasta():
    return SceneCopypastaRow(1, "text", 50, 20, 3, 2, "2026-07-10T00:00:00", "2026-07-17T00:00:00")


def _emote():
    return SceneWrappedEmoteRow(1, "PogChamp", "twitch", 300, 60)


def _event():
    return SceneEventRow(1, "record_stream", "2026-07-17T21:00:00", 1, "c1", "C1", 1, None, "T", "S", None)


def _patch(**overrides):
    defaults = {
        "select_scene_leaderboard_db": [],
        "select_scene_peak_viewers_db": [],
        "select_scene_active_chatters_db": 0,
        "select_scene_chatter_rankings_db": ([], False),
        "select_scene_highlights_db": ([], False),
        "select_scene_copypastas_db": ([], 0),
        "select_scene_emotes_db": [],
        "select_scene_events_db": ([], 0),
    }
    defaults.update(overrides)
    stack = ExitStack()
    for name, value in defaults.items():
        stack.enter_context(patch(f"{_QUERY}.{name}", return_value=value))
    return stack


def test_totals_and_peak_merge():
    with _patch(
        select_scene_leaderboard_db=[_lb(1, 3, 6.0, 1000), _lb(2, 2, 4.0, 500)],
        select_scene_peak_viewers_db=[ScenePeakViewerRow(2, 1234)],
        select_scene_active_chatters_db=99,
    ):
        wrapped = get_scene_wrapped(30)

    assert wrapped.days == 30
    assert wrapped.totals.streams == 5
    assert wrapped.totals.hours_streamed == 10.0
    assert wrapped.totals.messages == 1500
    assert wrapped.totals.active_chatters == 99
    assert wrapped.totals.creators_active == 2
    # Peak merged only for creator 2; creator 1 has no sample -> None.
    assert wrapped.top_creators[0].creator_id == 1
    assert wrapped.top_creators[0].peak_viewers is None
    assert wrapped.top_creators[1].peak_viewers == 1234
    assert [c.rank for c in wrapped.top_creators] == [1, 2]


def test_empty_scene_hours_is_unknown():
    with _patch():
        wrapped = get_scene_wrapped(7)
    assert wrapped.totals.hours_streamed is None
    assert wrapped.totals.streams == 0
    assert wrapped.top_creators == []
    assert wrapped.notable_events == []


def test_top_creators_truncated_to_five():
    with _patch(select_scene_leaderboard_db=[_lb(i, 1, 1.0, 100 - i) for i in range(1, 9)]):
        wrapped = get_scene_wrapped(30)
    assert len(wrapped.top_creators) == 5
    assert [c.rank for c in wrapped.top_creators] == [1, 2, 3, 4, 5]


def test_moment_twitch_id_stringified_and_lists_flow():
    with _patch(
        select_scene_chatter_rankings_db=([_chatter(1)], False),
        select_scene_highlights_db=([_highlight()], False),
        select_scene_copypastas_db=([_copypasta()], 1),
        select_scene_emotes_db=[_emote()],
        select_scene_events_db=([_event()], 1),
    ):
        wrapped = get_scene_wrapped(30)

    assert wrapped.top_chatters[0].rank == 1
    assert wrapped.top_moments[0].twitch_id == "42"
    assert wrapped.top_copypastas[0].creator_count == 2
    assert wrapped.top_emotes[0].name == "PogChamp"
    assert wrapped.notable_events[0].event_type == "record_stream"
