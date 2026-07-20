"""Application query assembling a chatter head-to-head from the chatter rollups.

Mirrors the creator ``head_to_head_query`` shape: identity + per-side aggregates
plus one pairwise co-attendance read. Sides are built from the shared
``load_chatter_aggregates`` pipeline (loyalty rollup for totals, message-time
bounds, archetype badges) so the comparison never contradicts either chatter's
passport.
"""

from datetime import UTC, datetime

from stream_sniper.database.gateways.community.chatter_pair_gateway import select_chatter_pair_shared_db

from .chatter_aggregates import load_chatter_aggregates
from .versus_models import ChatterHeadToHead, VersusChatter


class ChatterVersusNotFoundError(LookupError):
    """One or both chatter ids are unknown."""


def _side(chatter_id: int, now: datetime) -> VersusChatter | None:
    aggregates = load_chatter_aggregates(chatter_id, now=now)
    if aggregates is None:
        return None

    return VersusChatter(
        chatter_id=aggregates.identity.id,
        nick=aggregates.identity.nick,
        is_bot=aggregates.identity.is_bot,
        messages=aggregates.total_messages,
        streams_attended=aggregates.streams_attended,
        creators_visited=len(aggregates.loyalty_rows),
        first_seen=aggregates.time_bounds.first_message_time,
        last_seen=aggregates.time_bounds.last_message_time,
        home_channel=aggregates.home_channel,
        archetypes=aggregates.archetypes,
    )


def get_chatter_head_to_head(chatter_a: int, chatter_b: int) -> ChatterHeadToHead:
    """Assemble the pairwise comparison; raises when either chatter id is unknown.

    A pair that never shared a stream is a legitimate zero. Callers pass a
    normalized (lo, hi) pair, so side ``a`` is the lower chatter id.
    """
    now = datetime.now(UTC)
    side_a = _side(chatter_a, now)
    side_b = _side(chatter_b, now)
    if side_a is None or side_b is None:
        missing = [cid for cid, side in ((chatter_a, side_a), (chatter_b, side_b)) if side is None]
        raise ChatterVersusNotFoundError(f"Unknown chatters: {missing}")

    shared = select_chatter_pair_shared_db(chatter_a, chatter_b)
    return ChatterHeadToHead(
        a=side_a,
        b=side_b,
        shared_streams=shared.shared_streams,
        shared_creators=shared.shared_creators,
    )
