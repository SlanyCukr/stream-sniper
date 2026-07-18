"""Unit tests for the Creator Wrapped assembly (get_creator_wrapped).

Gateways are monkeypatched at the ``wrapped_query`` import path; this suite asserts the
FastAPI-free assembly directly (existence check -> CreatorNotFoundError, totals
passthrough, top-N truncation and 1-based ranking, empty-window zeros).
"""

from contextlib import ExitStack
from unittest.mock import patch

import pytest

from stream_sniper.application.creators.analytics_query import CreatorNotFoundError
from stream_sniper.application.creators.wrapped_query import get_creator_wrapped
from stream_sniper.database.gateways.content.records import SceneCopypastaRow
from stream_sniper.database.gateways.content.scene_highlights_gateway import SceneHighlightRow
from stream_sniper.database.gateways.content.scene_wrapped_gateway import SceneWrappedEmoteRow
from stream_sniper.database.gateways.creators.creator_wrapped_gateway import (
    CreatorWrappedChatterRow,
    CreatorWrappedTotalsRow,
)

_QUERY = "stream_sniper.application.creators.wrapped_query"


def _totals(streams=3, hours=6.0, messages=1000):
    return CreatorWrappedTotalsRow(streams=streams, hours_streamed=hours, messages=messages)


def _chatter(chatter_id, messages=100):
    return CreatorWrappedChatterRow(
        chatter_id=chatter_id,
        nick=f"ch{chatter_id}",
        total_messages=messages,
        streams_attended=2,
    )


def _highlight():
    return SceneHighlightRow(
        stream_id=1,
        stream_title="S1",
        twitch_id=42,
        creator_id=5,
        creator_nick="c5",
        creator_display_name="C5",
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
    return SceneCopypastaRow(1, "text", 50, 20, 3, 1, "2026-07-10T00:00:00", "2026-07-17T00:00:00")


def _emote():
    return SceneWrappedEmoteRow(1, "PogChamp", "twitch", 300, 60)


def _patch(*, exists=True, **overrides):
    defaults = {
        "select_creator_wrapped_totals_db": _totals(),
        "select_creator_active_chatters_db": 0,
        "select_creator_wrapped_chatters_db": ([], False),
        "select_scene_highlights_db": ([], False),
        "select_scene_copypastas_db": ([], 0),
        "select_creator_wrapped_emotes_db": [],
    }
    defaults.update(overrides)
    stack = ExitStack()
    stack.enter_context(patch(f"{_QUERY}.select_creator_exists_db", return_value=exists))
    for name, value in defaults.items():
        stack.enter_context(patch(f"{_QUERY}.{name}", return_value=value))
    return stack


def test_unknown_creator_raises_not_found():
    with _patch(exists=False):
        with pytest.raises(CreatorNotFoundError):
            get_creator_wrapped(999, 30)


def test_totals_and_active_chatters_passthrough():
    with _patch(
        select_creator_wrapped_totals_db=_totals(streams=5, hours=12.0, messages=2000),
        select_creator_active_chatters_db=42,
    ):
        wrapped = get_creator_wrapped(5, 30)

    assert wrapped.creator_id == 5
    assert wrapped.days == 30
    assert wrapped.totals.streams == 5
    assert wrapped.totals.hours_streamed == 12.0
    assert wrapped.totals.messages == 2000
    assert wrapped.totals.active_chatters == 42


def test_empty_window_hours_is_unknown_not_zero():
    with _patch(select_creator_wrapped_totals_db=CreatorWrappedTotalsRow(0, None, 0)):
        wrapped = get_creator_wrapped(5, 7)

    assert wrapped.totals.streams == 0
    assert wrapped.totals.hours_streamed is None
    assert wrapped.totals.messages == 0
    assert wrapped.top_chatters == []
    assert wrapped.top_moments == []
    assert wrapped.top_copypastas == []
    assert wrapped.top_emotes == []


def test_top_chatters_ranked_and_truncated_to_five():
    with _patch(
        select_creator_wrapped_chatters_db=([_chatter(i, messages=100 - i) for i in range(1, 6)], False)
    ):
        wrapped = get_creator_wrapped(5, 30)

    assert [c.rank for c in wrapped.top_chatters] == [1, 2, 3, 4, 5]
    assert wrapped.top_chatters[0].chatter_id == 1


def test_moment_twitch_id_stringified_and_copypasta_emote_flow():
    with _patch(
        select_scene_highlights_db=([_highlight()], False),
        select_scene_copypastas_db=([_copypasta()], 1),
        select_creator_wrapped_emotes_db=[_emote()],
    ):
        wrapped = get_creator_wrapped(5, 30)

    assert wrapped.top_moments[0].twitch_id == "42"
    assert wrapped.top_moments[0].ratio == 3.0
    assert wrapped.top_copypastas[0].message_text_id == 1
    assert wrapped.top_copypastas[0].stream_count == 3
    assert wrapped.top_emotes[0].name == "PogChamp"


def test_moment_and_copypasta_gateways_scoped_to_creator():
    with _patch() as stack:
        mock_highlights = stack.enter_context(
            patch(f"{_QUERY}.select_scene_highlights_db", return_value=([], False))
        )
        mock_copypastas = stack.enter_context(
            patch(f"{_QUERY}.select_scene_copypastas_db", return_value=([], 0))
        )
        get_creator_wrapped(5, 14)

    mock_highlights.assert_called_once_with(14, 5, "hype", 3, 0)
    mock_copypastas.assert_called_once_with(14, 5, "usage", 3, 0)
