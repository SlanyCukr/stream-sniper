"""Read-only endpoints for community overlap (shared-audience map + creator neighbors)."""

from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response

from ..database.creator_overlap_table_gateway import (
    select_creator_neighbors_db,
    select_overlap_db,
)
from ..logging_config import get_logger
from .cache import CacheTTL, get_cache
from .community_models import (
    CommunityOverlap,
    CreatorNeighbor,
    CreatorNeighbors,
    OverlapCreator,
    OverlapPair,
)
from .models import ErrorResponse
from .monitoring import record_cache_operation
from .rate_limiter import limiter, rate_limits

logger = get_logger(__name__)

router = APIRouter(tags=["Community"])

# Endpoint metric name -> gateway pair column (shared_*). Whitelisted so the caller value
# never reaches SQL directly.
_NEIGHBOR_METRIC_COLUMN = {
    "chatters": "shared_chatters",
    "regulars": "shared_regulars",
}


def _jaccard(shared: int, size_a: int, size_b: int) -> Optional[float]:
    """shared / union; None when the union is 0 (both audiences empty)."""
    union = size_a + size_b - shared
    if union <= 0:
        return None
    return round(shared / union, 4)


@router.get(
    "/community/overlap",
    response_model=CommunityOverlap,
    summary="Get the community overlap map",
    description="Top creators by audience size and the shared-audience overlap among them.",
    responses={
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_community_overlap(
    request: Request,
    response: Response,
    limit: int = Query(40, description="Number of top creators to include", ge=1, le=60),
) -> CommunityOverlap:
    """Get the overlap map for the top-`limit` creators by audience size.

    Jaccard is computed here from audience denominators and is null when the union is 0.
    """
    try:
        cache = get_cache()
        cache_key = cache._generate_key("community_overlap", limit)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "community_overlap")
            return CommunityOverlap(**cached_result)

        record_cache_operation("miss", "community_overlap")
        creator_rows, pair_rows = select_overlap_db(limit)

        creators = [
            OverlapCreator(
                creator_id=row[0],
                nick=row[1],
                display_name=row[2],
                chatters=row[3],
                regulars=row[4],
            )
            for row in creator_rows
        ]
        computed_at = creator_rows[0][5] if creator_rows else None

        sizes = {row[0]: (row[3], row[4]) for row in creator_rows}
        pairs = []
        for pair in pair_rows:
            creator_a, creator_b, shared_chatters, shared_regulars = pair
            chatters_a, regulars_a = sizes.get(creator_a, (0, 0))
            chatters_b, regulars_b = sizes.get(creator_b, (0, 0))
            pairs.append(
                OverlapPair(
                    a=creator_a,
                    b=creator_b,
                    shared_chatters=shared_chatters,
                    shared_regulars=shared_regulars,
                    jaccard_chatters=_jaccard(shared_chatters, chatters_a, chatters_b),
                    jaccard_regulars=_jaccard(shared_regulars, regulars_a, regulars_b),
                )
            )

        result = CommunityOverlap(creators=creators, pairs=pairs, computed_at=computed_at)
        cache.set(cache_key, result.model_dump(), CacheTTL.STREAM_ANALYTICS)
        record_cache_operation("set", "community_overlap")
        response.headers["X-Cache"] = "MISS"
        return result
    except Exception as exc:
        logger.error(f"Error fetching community overlap: {exc}")
        record_cache_operation("error", "community_overlap")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/community/creator/{creator_id}/neighbors",
    response_model=CreatorNeighbors,
    summary="Get a creator's audience neighbors",
    description="Ranked 'audience also watches' creators sharing the most audience with this one.",
    responses={
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_creator_neighbors(
    request: Request,
    response: Response,
    creator_id: int = Path(..., description="Creator ID", json_schema_extra={"example": 5}),
    metric: str = Query("regulars", pattern="^(chatters|regulars)$"),
    limit: int = Query(10, description="Number of neighbors to return", ge=1, le=50),
) -> CreatorNeighbors:
    """Get the creators whose audiences most overlap with this creator's."""
    try:
        cache = get_cache()
        cache_key = cache._generate_key("creator_neighbors", creator_id, metric, limit)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "creator_neighbors")
            return CreatorNeighbors(**cached_result)

        record_cache_operation("miss", "creator_neighbors")
        column = _NEIGHBOR_METRIC_COLUMN[metric]
        rows = select_creator_neighbors_db(creator_id, column, limit)

        neighbors = [
            CreatorNeighbor(
                creator_id=row[0],
                nick=row[1],
                display_name=row[2],
                shared_chatters=row[3],
                shared_regulars=row[4],
            )
            for row in rows
        ]
        result = CreatorNeighbors(creator_id=creator_id, metric=metric, neighbors=neighbors)
        cache.set(cache_key, result.model_dump(), CacheTTL.STREAM_ANALYTICS)
        record_cache_operation("set", "creator_neighbors")
        response.headers["X-Cache"] = "MISS"
        return result
    except Exception as exc:
        logger.error(f"Error fetching creator neighbors: {exc}")
        record_cache_operation("error", "creator_neighbors")
        raise HTTPException(status_code=500, detail="Internal server error")
