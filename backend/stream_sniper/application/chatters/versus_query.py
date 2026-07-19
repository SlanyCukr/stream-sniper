"""Application query assembling a chatter head-to-head from the chatter rollups.

Mirrors the creator ``head_to_head_query`` shape: identity + per-side aggregates
plus one pairwise co-attendance read. Sides reuse the passport's aggregation
rules (loyalty rollup for totals, message-time bounds, archetype badges) so the
comparison never contradicts either chatter's passport.
"""

from datetime import UTC, datetime

from stream_sniper.database.gateways.analytics.stream_chatter_stats_table_gateway import (
    select_chatter_message_time_bounds_db,
)
from stream_sniper.database.gateways.chat.chatter_table_gateway import select_chatter_profile_db
from stream_sniper.database.gateways.community.chatter_pair_gateway import select_chatter_pair_shared_db
from stream_sniper.database.gateways.creators.creator_chatter_stats_table_gateway import select_chatter_loyalty_db

from .archetypes import compute_archetypes
from .passport_models import PassportHomeChannel
from .versus_models import ChatterHeadToHead, VersusChatter


class ChatterVersusNotFoundError(LookupError):
    """One or both chatter ids are unknown."""


def _side(chatter_id: int, now: datetime) -> VersusChatter | None:
    identity = select_chatter_profile_db(chatter_id)
    if identity is None:
        return None

    loyalty_rows = select_chatter_loyalty_db(chatter_id)
    total_messages = sum(row.message_count for row in loyalty_rows)
    home_channel = (
        PassportHomeChannel.from_row(loyalty_rows[0], total_messages=total_messages) if loyalty_rows else None
    )
    time_bounds = select_chatter_message_time_bounds_db(chatter_id)
    streams_attended = sum(row.streams_attended for row in loyalty_rows)

    return VersusChatter(
        chatter_id=identity.id,
        nick=identity.nick,
        is_bot=identity.is_bot,
        messages=total_messages,
        streams_attended=streams_attended,
        creators_visited=len(loyalty_rows),
        first_seen=time_bounds.first_message_time,
        last_seen=time_bounds.last_message_time,
        home_channel=home_channel,
        archetypes=compute_archetypes(
            total_messages=total_messages,
            streams_attended=streams_attended,
            creators_visited=len(loyalty_rows),
            home_share=home_channel.share if home_channel is not None else None,
            first_seen=time_bounds.first_message_time,
            now=now,
        ),
    )


def get_chatter_head_to_head(chatter_a: int, chatter_b: int) -> ChatterHeadToHead:
    """Assemble the pairwise comparison; raises when either chatter id is unknown.

    A pair that never shared a stream is a legitimate zero. Callers pass a
    normalized (lo, hi) pair, so side ``a`` is the lower chatter id.
    """
    now = datetime.now(UTC)
    side_a = _side(chatter_a, now)
    side_b = _side(chatter_b, now)
    missing = [cid for cid, side in ((chatter_a, side_a), (chatter_b, side_b)) if side is None]
    if missing or side_a is None or side_b is None:
        raise ChatterVersusNotFoundError(f"Unknown chatters: {missing}")

    shared = select_chatter_pair_shared_db(chatter_a, chatter_b)
    return ChatterHeadToHead(
        a=side_a,
        b=side_b,
        shared_streams=shared.shared_streams,
        shared_creators=shared.shared_creators,
    )
