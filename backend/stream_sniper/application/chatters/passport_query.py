"""Application query assembling a public per-chatter identity passport.

Spans three gateways: the chatter table (identity + bot flag), the
creator_chatter_stats rollup (totals, loyalty, home channel), and the
stream_chatter_stats rollup (debut, most-active-stream milestone). Returns
``None`` when the chatter id is unknown so the HTTP layer can 404.
"""

from stream_sniper.database.gateways.analytics.stream_chatter_stats_table_gateway import (
    select_chatter_debut_db,
    select_chatter_message_time_bounds_db,
    select_chatter_most_active_stream_db,
)
from stream_sniper.database.gateways.chat.chatter_table_gateway import select_chatter_profile_db
from stream_sniper.database.gateways.creators.creator_chatter_stats_table_gateway import select_chatter_loyalty_db

from .passport_models import (
    ChatterPassport,
    PassportChatter,
    PassportDebut,
    PassportHomeChannel,
    PassportLoyalty,
    PassportMilestones,
    PassportMostActiveStream,
    PassportTotals,
)


def get_chatter_passport(chatter_id: int) -> ChatterPassport | None:
    """Assemble the passport from explicit rollup sources, or None if unknown."""
    identity = select_chatter_profile_db(chatter_id)
    if identity is None:
        return None

    loyalty_rows = select_chatter_loyalty_db(chatter_id)

    total_messages = sum(row.message_count for row in loyalty_rows)
    # Lifetime bounds come from actual MESSAGE times (stream_chatter_stats), not the
    # creator_chatter_stats first/last_seen_at columns — those record attended-stream
    # START times and would contradict the debut card for late-arriving chatters.
    time_bounds = select_chatter_message_time_bounds_db(chatter_id)
    totals = PassportTotals(
        messages=total_messages,
        streams_attended=sum(row.streams_attended for row in loyalty_rows),
        creators_visited=len(loyalty_rows),
        first_seen=time_bounds.first_message_time,
        last_seen=time_bounds.last_message_time,
    )

    loyalty = [PassportLoyalty.from_row(row, total_messages=total_messages) for row in loyalty_rows]
    home_channel = (
        PassportHomeChannel.from_row(loyalty_rows[0], total_messages=total_messages) if loyalty_rows else None
    )

    debut_row = select_chatter_debut_db(chatter_id)
    active_row = select_chatter_most_active_stream_db(chatter_id)

    return ChatterPassport(
        chatter=PassportChatter.from_row(identity),
        totals=totals,
        debut=PassportDebut.from_row(debut_row) if debut_row is not None else None,
        home_channel=home_channel,
        loyalty=loyalty,
        milestones=PassportMilestones(
            most_active_stream=(
                PassportMostActiveStream.from_row(active_row) if active_row is not None else None
            )
        ),
    )
