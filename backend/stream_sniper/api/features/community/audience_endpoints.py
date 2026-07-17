"""Window-over-window creator audience participation reports."""

from fastapi import APIRouter, Path, Query, Request, Response

from ....application.community.audience_models import AudienceMovement
from ....application.community.audience_query import get_audience_movement as query_audience_movement
from ....logging_config import get_logger
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy
from ...caching.rollup_version import creator_rollup_version
from ...dependencies import get_cache
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import RateLimitErrorResponse

logger = get_logger(__name__)
router = APIRouter(tags=["Community"])
_AUDIENCE_MOVEMENT_CACHE = ModelCachePolicy("audience_movement", CacheTTL.STREAM_ANALYTICS, AudienceMovement)


@router.get(
    "/creators/{creator_id}/audience-movement",
    response_model=AudienceMovement,
    responses={429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.HEAVY)
def get_audience_movement(
    request: Request,
    response: Response,
    creator_id: int = Path(..., ge=1),
    days: int = Query(30, ge=7, le=90),
    limit: int = Query(8, ge=1, le=20),
) -> AudienceMovement:
    """Compare distinct participating chatters across adjacent equal windows."""
    with _AUDIENCE_MOVEMENT_CACHE.record_failures():
        cache = get_cache(request)
        key, cached = _AUDIENCE_MOVEMENT_CACHE.lookup(
            cache, response, creator_id, days, limit, creator_rollup_version(creator_id)
        )
        if cached is not None:
            return cached
        result = query_audience_movement(creator_id, days, limit)
        _AUDIENCE_MOVEMENT_CACHE.store(cache, response, key, result)
        return result
