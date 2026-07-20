"""Application query assembling a public per-chatter identity passport.

Spans three gateways: the chatter table (identity + bot flag), the
creator_chatter_stats rollup (totals, loyalty, home channel), and the
stream_chatter_stats rollup (debut, most-active-stream milestone). Returns
``None`` when the chatter id is unknown so the HTTP layer can 404.
"""

from datetime import UTC, datetime

from stream_sniper.database.gateways.analytics.stream_chatter_stats_table_gateway import (
    select_chatter_debut_db,
    select_chatter_most_active_stream_db,
)
from stream_sniper.database.gateways.community.chat_companions_gateway import select_chat_companions_db

from .chatter_aggregates import load_chatter_aggregates
from .passport_models import (
    ChatterPassport,
    PassportChatter,
    PassportCompanion,
    PassportDebut,
    PassportLoyalty,
    PassportMilestones,
    PassportMostActiveStream,
    PassportTotals,
)


def get_chatter_passport(chatter_id: int) -> ChatterPassport | None:
    """Assemble the passport from explicit rollup sources, or None if unknown."""
    # now=UTC keeps the age-based archetype badges deterministic per request.
    aggregates = load_chatter_aggregates(chatter_id, now=datetime.now(UTC))
    if aggregates is None:
        return None

    totals = PassportTotals(
        messages=aggregates.total_messages,
        streams_attended=aggregates.streams_attended,
        creators_visited=len(aggregates.loyalty_rows),
        first_seen=aggregates.time_bounds.first_message_time,
        last_seen=aggregates.time_bounds.last_message_time,
    )
    loyalty = [
        PassportLoyalty.from_row(row, total_messages=aggregates.total_messages)
        for row in aggregates.loyalty_rows
    ]

    debut_row = select_chatter_debut_db(chatter_id)
    active_row = select_chatter_most_active_stream_db(chatter_id)
    companion_rows = select_chat_companions_db(chatter_id)

    return ChatterPassport(
        chatter=PassportChatter.from_row(aggregates.identity),
        totals=totals,
        debut=PassportDebut.from_row(debut_row) if debut_row is not None else None,
        home_channel=aggregates.home_channel,
        loyalty=loyalty,
        milestones=PassportMilestones(
            most_active_stream=(
                PassportMostActiveStream.from_row(active_row) if active_row is not None else None
            )
        ),
        archetypes=aggregates.archetypes,
        companions=[PassportCompanion.from_row(row) for row in companion_rows],
    )
