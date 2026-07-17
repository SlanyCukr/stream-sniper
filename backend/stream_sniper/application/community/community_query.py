"""Application queries for community overlap read models."""

from stream_sniper.database.gateways.community.creator_overlap_table_gateway import (
    select_creator_neighbors_db,
    select_overlap_db,
)
from stream_sniper.database.gateways.community.records import CommunityPairRow

from .models import (
    CommunityOverlap,
    CreatorNeighbor,
    CreatorNeighbors,
    OverlapCreator,
    OverlapPair,
)

_NEIGHBOR_METRIC_COLUMN = {
    "chatters": "shared_chatters",
    "regulars": "shared_regulars",
}


def jaccard(shared: int, size_a: int, size_b: int) -> float | None:
    """Return shared/union, or ``None`` for two empty audiences."""
    union = size_a + size_b - shared
    if union <= 0:
        return None
    return round(shared / union, 4)


def _pair(row: CommunityPairRow, sizes: dict[int, tuple[int, int]]) -> OverlapPair:
    creator_a = row.creator_a
    creator_b = row.creator_b
    shared_chatters = row.shared_chatters
    shared_regulars = row.shared_regulars
    chatters_a, regulars_a = sizes.get(creator_a, (0, 0))
    chatters_b, regulars_b = sizes.get(creator_b, (0, 0))
    return OverlapPair(
        a=creator_a,
        b=creator_b,
        shared_chatters=shared_chatters,
        shared_regulars=shared_regulars,
        jaccard_chatters=jaccard(shared_chatters, chatters_a, chatters_b),
        jaccard_regulars=jaccard(shared_regulars, regulars_a, regulars_b),
    )


def get_community_overlap(limit: int) -> CommunityOverlap:
    """Load creator audiences and calculate typed pair overlap metrics."""
    creator_rows, pair_rows = select_overlap_db(limit)
    creators = [
        OverlapCreator(
            creator_id=row.creator_id,
            nick=row.nick,
            display_name=row.display_name,
            chatters=row.chatters,
            regulars=row.regulars,
        )
        for row in creator_rows
    ]
    sizes = {row.creator_id: (row.chatters, row.regulars) for row in creator_rows}
    pairs = [_pair(row, sizes) for row in pair_rows]
    computed_at = creator_rows[0].computed_at if creator_rows else None
    return CommunityOverlap(creators=creators, pairs=pairs, computed_at=computed_at)


def get_creator_neighbors(
    creator_id: int,
    metric: str,
    limit: int,
) -> CreatorNeighbors:
    """Load the creators with the largest audience overlap."""
    column = _NEIGHBOR_METRIC_COLUMN[metric]
    rows = select_creator_neighbors_db(creator_id, column, limit)
    neighbors = [
        CreatorNeighbor(
            creator_id=row.creator_id,
            nick=row.nick,
            display_name=row.display_name,
            shared_chatters=row.shared_chatters,
            shared_regulars=row.shared_regulars,
        )
        for row in rows
    ]
    return CreatorNeighbors(creator_id=creator_id, metric=metric, neighbors=neighbors)
