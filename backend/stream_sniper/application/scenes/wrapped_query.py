"""Application-owned assembly for the Scene Wrapped period recap.

Fans out to the existing scene gateways (leaderboard, peak viewers, chatter rankings,
highlights, copypastas, events) plus the recap's two bespoke aggregates
(emotes + active-chatter count), then builds a single :class:`SceneWrapped` over the
trailing ``days`` window. Every source is already windowed; an empty scene simply yields
zero totals and empty lists (never a 404).
"""

from ...database.gateways.content.scene_event_table_gateway import select_scene_events_db
from ...database.gateways.content.scene_highlights_gateway import select_scene_highlights_db
from ...database.gateways.content.scene_table_gateway import (
    select_scene_leaderboard_db,
    select_scene_peak_viewers_db,
)
from ...database.gateways.content.scene_wrapped_gateway import (
    select_scene_active_chatters_db,
    select_scene_emotes_db,
)
from ...database.gateways.content.stream_copypasta_stats_table_gateway import select_scene_copypastas_db
from ...database.gateways.creators.scene_chatter_rankings_gateway import select_scene_chatter_rankings_db
from .wrapped_models import (
    SceneWrapped,
    WrappedChatter,
    WrappedCopypasta,
    WrappedCreator,
    WrappedEmote,
    WrappedEvent,
    WrappedMoment,
    WrappedTotals,
)

_TOP_CREATORS = 5
_TOP_CHATTERS = 5
_TOP_MOMENTS = 3
_TOP_COPYPASTAS = 3
_TOP_EMOTES = 5
_MAX_EVENTS = 8


def get_scene_wrapped(days: int) -> SceneWrapped:
    """Assemble the Scene Wrapped recap over the trailing ``days`` window.

    Aggregates the FULL leaderboard for the totals (streams / hours / messages /
    creators_active), merges peak viewers into the top-creator slice, and pulls the top
    chatters, moments, copypastas, emotes, and events from their respective gateways.
    """
    leaderboard = select_scene_leaderboard_db(days)
    peak_by_creator = {row.creator_id: row.peak_viewers for row in select_scene_peak_viewers_db(days)}
    active_chatters = select_scene_active_chatters_db(days)

    # Per-creator hours are never NULL (unclosed streams contribute 0h via a SQL CASE), so
    # a present sum is meaningful; an empty scene has no streamed time at all -> unknown.
    hours_values = [row.hours_streamed for row in leaderboard if row.hours_streamed is not None]
    totals = WrappedTotals(
        streams=sum(row.streams for row in leaderboard),
        hours_streamed=sum(hours_values) if hours_values else None,
        messages=sum(row.total_messages for row in leaderboard),
        active_chatters=active_chatters,
        creators_active=len(leaderboard),
    )

    top_creators = [
        WrappedCreator(
            rank=rank,
            creator_id=row.creator_id,
            nick=row.nick,
            display_name=row.display_name,
            profile_image_url=row.profile_image_url,
            total_messages=row.total_messages,
            streams=row.streams,
            hours_streamed=row.hours_streamed,
            msgs_per_min=row.msgs_per_min,
            peak_viewers=peak_by_creator.get(row.creator_id),
        )
        for rank, row in enumerate(leaderboard[:_TOP_CREATORS], start=1)
    ]

    chatter_rows, _ = select_scene_chatter_rankings_db(days, _TOP_CHATTERS, 0)
    top_chatters = [
        WrappedChatter(
            rank=rank,
            chatter_id=row.chatter_id,
            nick=row.nick,
            total_messages=row.total_messages,
            streams_attended=row.streams_attended,
            creators_visited=row.creators_visited,
            home_creator_display_name=row.home_creator_display_name,
        )
        for rank, row in enumerate(chatter_rows, start=1)
    ]

    moment_rows, _ = select_scene_highlights_db(days, None, "hype", _TOP_MOMENTS, 0)
    top_moments = [
        WrappedMoment(
            stream_id=row.stream_id,
            stream_title=row.stream_title,
            twitch_id=str(row.twitch_id) if row.twitch_id is not None else None,
            creator_display_name=row.creator_display_name,
            bucket_minute=row.bucket_minute,
            offset_seconds=row.offset_seconds,
            ratio=row.ratio,
            message_count=row.message_count,
        )
        for row in moment_rows
    ]

    copypasta_rows, _ = select_scene_copypastas_db(days, None, "usage", _TOP_COPYPASTAS, 0)
    top_copypastas = [
        WrappedCopypasta(
            message_text_id=row.message_text_id,
            text=row.text,
            usage_count=row.usage_count,
            creator_count=row.creator_count,
            stream_count=row.stream_count,
        )
        for row in copypasta_rows
    ]

    top_emotes = [
        WrappedEmote(
            emote_id=row.emote_id,
            name=row.name,
            source=row.source,
            usage=row.usage,
            chatter_reach=row.chatter_reach,
        )
        for row in select_scene_emotes_db(days, _TOP_EMOTES)
    ]

    event_rows, _ = select_scene_events_db(days, None, None, _MAX_EVENTS, 0)
    notable_events = [
        WrappedEvent(
            event_type=row.event_type,
            occurred_at=row.occurred_at,
            title=row.title,
            summary=row.summary,
            creator_display_name=row.creator_display_name,
        )
        for row in event_rows
    ]

    return SceneWrapped(
        days=days,
        totals=totals,
        top_creators=top_creators,
        top_chatters=top_chatters,
        top_moments=top_moments,
        top_copypastas=top_copypastas,
        top_emotes=top_emotes,
        notable_events=notable_events,
    )
