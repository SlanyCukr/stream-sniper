"""Shared rollup aggregation for one chatter, reused by the passport and versus queries.

Owns the aggregation rules both surfaces must agree on: the loyalty rollup for
totals and the home channel, message-time bounds for the lifetime era, and the
derived archetype badges. Keeping them in one place guarantees a head-to-head
side never contradicts that chatter's passport.
"""

from dataclasses import dataclass
from datetime import datetime

from stream_sniper.database.gateways.analytics.records import ChatterTimeBoundsRow
from stream_sniper.database.gateways.analytics.stream_chatter_stats_table_gateway import (
    select_chatter_message_time_bounds_db,
)
from stream_sniper.database.gateways.chat.chatter_table_gateway import select_chatter_profile_db
from stream_sniper.database.gateways.chat.records import ChatterProfileRow
from stream_sniper.database.gateways.creators.creator_chatter_stats_table_gateway import select_chatter_loyalty_db
from stream_sniper.database.gateways.creators.records import ChatterLoyaltyRow

from .archetypes import compute_archetypes
from .passport_models import PassportArchetype, PassportHomeChannel


@dataclass(frozen=True)
class ChatterAggregates:
    """Identity plus the rollup-derived aggregates for one chatter."""

    identity: ChatterProfileRow
    loyalty_rows: list[ChatterLoyaltyRow]
    total_messages: int
    streams_attended: int
    time_bounds: ChatterTimeBoundsRow
    home_channel: PassportHomeChannel | None
    archetypes: list[PassportArchetype]


def load_chatter_aggregates(chatter_id: int, *, now: datetime) -> ChatterAggregates | None:
    """Fetch and aggregate one chatter's rollups, or None when the id is unknown."""
    identity = select_chatter_profile_db(chatter_id)
    if identity is None:
        return None

    loyalty_rows = select_chatter_loyalty_db(chatter_id)
    total_messages = sum(row.message_count for row in loyalty_rows)
    # Lifetime bounds come from actual MESSAGE times (stream_chatter_stats), not the
    # creator_chatter_stats first/last_seen_at columns — those record attended-stream
    # START times and would contradict the debut card for late-arriving chatters.
    time_bounds = select_chatter_message_time_bounds_db(chatter_id)
    streams_attended = sum(row.streams_attended for row in loyalty_rows)
    home_channel = (
        PassportHomeChannel.from_row(loyalty_rows[0], total_messages=total_messages) if loyalty_rows else None
    )
    # Archetypes are derived purely from the aggregates assembled above (no extra query).
    return ChatterAggregates(
        identity=identity,
        loyalty_rows=loyalty_rows,
        total_messages=total_messages,
        streams_attended=streams_attended,
        time_bounds=time_bounds,
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
