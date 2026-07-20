"""Application-owned assembly for the Creator Wrapped period recap.

Mirrors ``scenes/wrapped_query.get_scene_wrapped`` scoped to a single creator: fans out
to the creator-scoped ``creator_wrapped_gateway`` aggregates (totals, chatters) plus the
scene wrapped/highlights/copypasta gateways, all of which accept an optional
``creator_id`` filter — no bespoke creator gateways were needed for active chatters,
emotes, moments, or copypastas. Unlike the scene recap, an unknown creator IS a 404: the caller
must check ``get_creator_wrapped`` for a :class:`CreatorNotFoundError` before trusting an
empty-looking recap.
"""

from ...database.gateways.content.scene_highlights_gateway import select_scene_highlights_db
from ...database.gateways.content.scene_wrapped_gateway import (
    select_scene_active_chatters_db,
    select_scene_emotes_db,
)
from ...database.gateways.content.stream_copypasta_stats_table_gateway import select_scene_copypastas_db
from ...database.gateways.creators.creator_wrapped_gateway import (
    select_creator_wrapped_chatters_db,
    select_creator_wrapped_totals_db,
)
from ...database.gateways.identity.creator_table_gateway import select_creator_exists_db
from .analytics_query import CreatorNotFoundError
from .wrapped_models import (
    CreatorWrapped,
    CreatorWrappedChatter,
    CreatorWrappedCopypasta,
    CreatorWrappedEmote,
    CreatorWrappedMoment,
    CreatorWrappedTotals,
)

_TOP_CHATTERS = 5
_TOP_MOMENTS = 3
_TOP_COPYPASTAS = 3
_TOP_EMOTES = 5


def get_creator_wrapped(creator_id: int, days: int) -> CreatorWrapped:
    """Assemble the Creator Wrapped recap for one creator over the trailing ``days`` window.

    Raises :class:`CreatorNotFoundError` when ``creator_id`` does not exist (matching
    ``get_creator_summary``'s contract); an existing creator with no activity in the
    window still returns 200 with zeroed totals and empty lists, same as the scene recap.
    """
    if not select_creator_exists_db(creator_id):
        raise CreatorNotFoundError

    totals_row = select_creator_wrapped_totals_db(creator_id, days)
    active_chatters = select_scene_active_chatters_db(days, creator_id=creator_id)
    totals = CreatorWrappedTotals(
        streams=totals_row.streams,
        hours_streamed=totals_row.hours_streamed,
        messages=totals_row.messages,
        active_chatters=active_chatters,
    )

    chatter_rows, _ = select_creator_wrapped_chatters_db(creator_id, days, _TOP_CHATTERS, 0)
    top_chatters = [
        CreatorWrappedChatter(
            rank=rank,
            chatter_id=row.chatter_id,
            nick=row.nick,
            total_messages=row.total_messages,
            streams_attended=row.streams_attended,
        )
        for rank, row in enumerate(chatter_rows, start=1)
    ]

    moment_rows, _ = select_scene_highlights_db(days, creator_id, "hype", _TOP_MOMENTS, 0)
    top_moments = [
        CreatorWrappedMoment(
            stream_id=row.stream_id,
            stream_title=row.stream_title,
            twitch_id=str(row.twitch_id) if row.twitch_id is not None else None,
            bucket_minute=row.bucket_minute,
            offset_seconds=row.offset_seconds,
            ratio=row.ratio,
            message_count=row.message_count,
        )
        for row in moment_rows
    ]

    copypasta_rows, _ = select_scene_copypastas_db(days, creator_id, "usage", _TOP_COPYPASTAS, 0)
    top_copypastas = [
        CreatorWrappedCopypasta(
            message_text_id=row.message_text_id,
            text=row.text,
            usage_count=row.usage_count,
            stream_count=row.stream_count,
        )
        for row in copypasta_rows
    ]

    top_emotes = [
        CreatorWrappedEmote(
            emote_id=row.emote_id,
            name=row.name,
            source=row.source,
            usage=row.usage,
            chatter_reach=row.chatter_reach,
        )
        for row in select_scene_emotes_db(days, _TOP_EMOTES, creator_id=creator_id)
    ]

    return CreatorWrapped(
        creator_id=creator_id,
        days=days,
        totals=totals,
        top_chatters=top_chatters,
        top_moments=top_moments,
        top_copypastas=top_copypastas,
        top_emotes=top_emotes,
    )
