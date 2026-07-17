"""Read-only endpoints for community overlap (shared-audience map + creator neighbors)."""

from fastapi import APIRouter, Path, Query, Request, Response

from ....application.community.community_query import (
    get_community_overlap as query_community_overlap,
)
from ....application.community.community_query import (
    get_creator_neighbors as query_creator_neighbors,
)
from ....application.community.models import (
    CommunityOverlap,
    CreatorNeighbors,
)
from ....logging_config import get_logger
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy
from ...dependencies import get_cache
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import RateLimitErrorResponse

logger = get_logger(__name__)

router = APIRouter(tags=["Community"])

_OVERLAP_CACHE = ModelCachePolicy("community_overlap", CacheTTL.STREAM_ANALYTICS, CommunityOverlap)
_NEIGHBORS_CACHE = ModelCachePolicy("creator_neighbors", CacheTTL.STREAM_ANALYTICS, CreatorNeighbors)


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
        cache_key, cached_result = _OVERLAP_CACHE.lookup(cache, response, limit)
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
        cache_key, cached_result = _NEIGHBORS_CACHE.lookup(cache, response, creator_id, metric, limit)
        if cached_result is not None:
            return cached_result

        result = query_creator_neighbors(creator_id, metric, limit)
        _NEIGHBORS_CACHE.store(cache, response, cache_key, result)
        return result
