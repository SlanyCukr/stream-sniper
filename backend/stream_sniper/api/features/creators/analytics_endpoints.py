"""Read-only endpoints for creator-level analytics (trends and regulars)."""

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response

from ....application.creators.analytics_models import CreatorSummary, CreatorTrends
from ....application.creators.analytics_query import (
    CreatorNotFoundError,
)
from ....application.creators.analytics_query import (
    get_creator_summary as query_creator_summary,
)
from ....application.creators.analytics_query import (
    get_creator_trends as query_creator_trends,
)
from ....application.creators.regulars_models import CreatorRegulars
from ....application.creators.regulars_query import get_creator_regulars as query_creator_regulars
from ....logging_config import get_logger
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy
from ...composition import CREATOR_REGULARS_SOURCES
from ...dependencies import get_cache
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import ErrorResponse, RateLimitErrorResponse

logger = get_logger(__name__)

router = APIRouter(tags=["Creators"])
_REGULARS_CACHE = ModelCachePolicy("creator_regulars", CacheTTL.STREAM_DETAILS, CreatorRegulars)
_TRENDS_CACHE = ModelCachePolicy("creator_trends", CacheTTL.STREAM_ANALYTICS, CreatorTrends)
_SUMMARY_CACHE = ModelCachePolicy("creator_summary", CacheTTL.STREAM_ANALYTICS, CreatorSummary)


@router.get(
    "/creators/{creator_id}/summary",
    response_model=CreatorSummary,
    summary="Get a creator dossier summary",
    description="Identity and lifetime analytics assembled from bounded rollup tables.",
    responses={
        404: {"model": ErrorResponse, "description": "Creator not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_creator_summary(
    request: Request,
    response: Response,
    creator_id: int = Path(..., description="Creator ID", json_schema_extra={"example": 5}),
) -> CreatorSummary:
    """Get the stable header and lifetime totals for a permanent creator page."""
    with _SUMMARY_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _SUMMARY_CACHE.lookup(cache, response, creator_id)
        if cached_result is not None:
            return cached_result
        try:
            result = query_creator_summary(creator_id)
        except CreatorNotFoundError as error:
            raise HTTPException(status_code=404, detail="Creator not found") from error
        _SUMMARY_CACHE.store(cache, response, cache_key, result)
        return result


@router.get(
    "/creators/{creator_id}/trends",
    response_model=CreatorTrends,
    summary="Get a creator's recent stream trends",
    description="Return per-stream metrics for a creator's most recent streams, ascending by start.",
    responses={
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_creator_trends(
    request: Request,
    response: Response,
    creator_id: int = Path(..., description="Creator ID", json_schema_extra={"example": 5}),
    limit: int = Query(20, description="Number of most-recent streams to include", ge=1, le=100),
) -> CreatorTrends:
    """Get per-stream trend points for a creator's recent streams."""
    with _TRENDS_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _TRENDS_CACHE.lookup(cache, response, creator_id, limit)
        if cached_result is not None:
            return cached_result

        result = query_creator_trends(creator_id, limit)
        _TRENDS_CACHE.store(cache, response, cache_key, result)
        return result


@router.get(
    "/creators/{creator_id}/regulars",
    response_model=CreatorRegulars,
    summary="Get a creator's recurring chatters",
    description="Return recurring chatters for a creator, ranked by attendance, with attendance rate.",
    responses={
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_creator_regulars(
    request: Request,
    response: Response,
    creator_id: int = Path(..., description="Creator ID", json_schema_extra={"example": 5}),
    sort: str = Query("attendance", pattern="^(attendance|streams|last_seen|messages)$"),
    dir: str = Query("desc", pattern="^(asc|desc)$"),
    min_streams: int = Query(2, description="Minimum streams attended to qualify", ge=1, le=1000),
    limit: int = Query(50, description="Maximum number of regulars to return", ge=1, le=200),
    include_bots: bool = Query(False, description="Include chatters flagged as bots"),
) -> CreatorRegulars:
    """Get a creator's recurring chatters with attendance rates."""
    with _REGULARS_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _REGULARS_CACHE.lookup(
            cache, response, creator_id, sort, dir, min_streams, limit, include_bots
        )
        if cached_result is not None:
            return cached_result

        result = query_creator_regulars(
            creator_id,
            min_streams,
            limit,
            CREATOR_REGULARS_SOURCES,
            sort=sort,
            direction=dir,
            include_bots=include_bots,
        )
        _REGULARS_CACHE.store(cache, response, cache_key, result)
        return result
