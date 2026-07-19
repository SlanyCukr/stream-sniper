"""Read-only endpoints for community overlap (shared-audience map + creator neighbors)."""

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response, status

from ....application.community.community_query import (
    get_community_overlap as query_community_overlap,
)
from ....application.community.community_query import (
    get_creator_neighbors as query_creator_neighbors,
)
from ....application.community.head_to_head_query import (
    HeadToHeadNotFoundError,
)
from ....application.community.head_to_head_query import (
    get_head_to_head as query_head_to_head,
)
from ....application.community.models import (
    CommunityOverlap,
    CreatorHeadToHead,
    CreatorNeighbors,
)
from ....logging_config import get_logger
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy
from ...caching.rollup_version import scene_rollup_version
from ...dependencies import get_cache
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import RateLimitErrorResponse

logger = get_logger(__name__)

router = APIRouter(tags=["Community"])

_OVERLAP_CACHE = ModelCachePolicy("community_overlap", CacheTTL.STREAM_ANALYTICS, CommunityOverlap)
_NEIGHBORS_CACHE = ModelCachePolicy("creator_neighbors", CacheTTL.STREAM_ANALYTICS, CreatorNeighbors)
_HEAD_TO_HEAD_CACHE = ModelCachePolicy("creator_head_to_head", CacheTTL.STREAM_ANALYTICS, CreatorHeadToHead)


@router.get(
    "/community/head-to-head",
    response_model=CreatorHeadToHead,
    summary="Compare two creators' audiences head-to-head",
    description=(
        "Shared audience, jaccard, and each side's share of overlap for two creators. "
        "A pair that never co-attended is a legitimate zero, not a 404."
    ),
    responses={
        404: {"description": "One or both creators have no audience rollup yet"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_creator_head_to_head(
    request: Request,
    response: Response,
    creator_a: int = Query(..., description="First creator ID", ge=1),
    creator_b: int = Query(..., description="Second creator ID", ge=1),
) -> CreatorHeadToHead:
    """Pairwise audience comparison built from the overlap rollups."""
    if creator_a == creator_b:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pick two different creators to compare.",
        )
    with _HEAD_TO_HEAD_CACHE.record_failures():
        cache = get_cache(request)
        lo, hi = sorted((creator_a, creator_b))
        cache_key, cached_result = _HEAD_TO_HEAD_CACHE.lookup(cache, response, lo, hi, scene_rollup_version())
        if cached_result is not None:
            return cached_result

        try:
            # Normalized to (lo, hi) so the cached payload is order-independent:
            # side `a` is always the lower creator id, whatever the param order.
            result = query_head_to_head(lo, hi)
        except HeadToHeadNotFoundError:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No audience data for one of these creators yet. It appears after their first rollup.",
            ) from None
        _HEAD_TO_HEAD_CACHE.store(cache, response, cache_key, result)
        return result


@router.get(
    "/community/overlap",
    response_model=CommunityOverlap,
    summary="Get the community overlap map",
    description="Top creators by audience size and the shared-audience overlap among them.",
    responses={
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
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
    with _OVERLAP_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _OVERLAP_CACHE.lookup(cache, response, limit, scene_rollup_version())
        if cached_result is not None:
            return cached_result

        result = query_community_overlap(limit)
        _OVERLAP_CACHE.store(cache, response, cache_key, result)
        return result


@router.get(
    "/community/creators/{creator_id}/neighbors",
    response_model=CreatorNeighbors,
    summary="Get a creator's audience neighbors",
    description="Ranked 'audience also watches' creators sharing the most audience with this one.",
    responses={
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
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
    with _NEIGHBORS_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _NEIGHBORS_CACHE.lookup(
            cache, response, creator_id, metric, limit, scene_rollup_version()
        )
        if cached_result is not None:
            return cached_result

        result = query_creator_neighbors(creator_id, metric, limit)
        _NEIGHBORS_CACHE.store(cache, response, cache_key, result)
        return result
