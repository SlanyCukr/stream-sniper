"""Application query assembling a creator head-to-head from overlap rollups."""

from stream_sniper.database.gateways.community.creator_overlap_table_gateway import (
    select_creator_audiences_db,
    select_creator_pair_overlap_db,
)
from stream_sniper.database.gateways.community.records import CommunityCreatorRow

from .community_query import jaccard
from .models import CreatorHeadToHead, HeadToHeadCreator


class HeadToHeadNotFoundError(LookupError):
    """One or both creators have no audience rollup yet."""


def _share(shared: int, audience: int) -> float | None:
    """Fraction of this creator's audience that is shared; None for an empty audience."""
    if audience <= 0:
        return None
    return round(shared / audience, 4)


def _side(row: CommunityCreatorRow, shared_chatters: int, shared_regulars: int) -> HeadToHeadCreator:
    return HeadToHeadCreator(
        creator_id=row.creator_id,
        nick=row.nick,
        display_name=row.display_name,
        chatters=row.chatters,
        regulars=row.regulars,
        shared_chatter_share=_share(shared_chatters, row.chatters),
        shared_regular_share=_share(shared_regulars, row.regulars),
    )


def get_head_to_head(creator_a: int, creator_b: int) -> CreatorHeadToHead:
    """Assemble the pairwise comparison for two creators.

    A missing overlap row (pair never co-attended) is a legitimate zero, not an
    error — only a missing audience rollup raises.
    """
    audiences = {row.creator_id: row for row in select_creator_audiences_db([creator_a, creator_b])}
    missing = [cid for cid in (creator_a, creator_b) if cid not in audiences]
    if missing:
        raise HeadToHeadNotFoundError(f"No audience rollup for creators: {missing}")

    pair = select_creator_pair_overlap_db(creator_a, creator_b)
    shared_chatters = pair.shared_chatters if pair else 0
    shared_regulars = pair.shared_regulars if pair else 0

    row_a = audiences[creator_a]
    row_b = audiences[creator_b]
    return CreatorHeadToHead(
        a=_side(row_a, shared_chatters, shared_regulars),
        b=_side(row_b, shared_chatters, shared_regulars),
        shared_chatters=shared_chatters,
        shared_regulars=shared_regulars,
        jaccard_chatters=jaccard(shared_chatters, row_a.chatters, row_b.chatters),
        jaccard_regulars=jaccard(shared_regulars, row_a.regulars, row_b.regulars),
        computed_at=row_a.computed_at,
    )
