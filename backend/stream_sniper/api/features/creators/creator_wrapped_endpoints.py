"""Public read endpoint for the Creator Wrapped period recap.

One creator's version of the Scene Wrapped recap. Public (no auth), following the sibling creator/scene
endpoint conventions: sync ``def`` handler (psycopg2 blocks), ``request: Request`` +
``response: Response`` for slowapi, in-process TTL cache keyed on creator id + window +
the creator's rollup version, nullable = unknown, 404 on an unknown creator id (see
``analytics_endpoints.get_creator_summary``). The multi-gateway assembly lives in
``application/creators/wrapped_query``; this handler owns only HTTP + caching.
"""

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response

from ....application.creators.analytics_query import CreatorNotFoundError
from ....application.creators.wrapped_models import CreatorWrapped
from ....application.creators.wrapped_query import get_creator_wrapped
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy
from ...caching.rollup_version import creator_rollup_version
from ...dependencies import get_cache
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import ErrorOrValidationResponse, ErrorResponse, RateLimitErrorResponse

router = APIRouter(tags=["Creators"])

_WRAPPED_CACHE = ModelCachePolicy("creator_wrapped", CacheTTL.STREAM_ANALYTICS, CreatorWrapped)


@router.get(
    "/creators/{creator_id}/wrapped",
    response_model=CreatorWrapped,
    summary="Get the Creator Wrapped period recap",
    description="A single creator's recap over a trailing window: totals plus top chatters, moments, "
    "copypastas, and emotes.",
    responses={
        404: {"model": ErrorResponse, "description": "Creator not found"},
        422: {"model": ErrorOrValidationResponse, "description": "Invalid window parameter"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_creator_wrapped_endpoint(
    request: Request,
    response: Response,
    creator_id: int = Path(..., description="Creator ID", json_schema_extra={"example": 5}),
    days: int = Query(30, ge=7, le=90, description="Recap window length in days (7-90)"),
) -> CreatorWrapped:
    """Get the Creator Wrapped recap for one creator over the trailing ``days`` window."""
    with _WRAPPED_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached = _WRAPPED_CACHE.lookup(cache, response, creator_id, days, creator_rollup_version(creator_id))
        if cached is not None:
            return cached

        try:
            result = get_creator_wrapped(creator_id, days)
        except CreatorNotFoundError as error:
            raise HTTPException(status_code=404, detail="Creator not found") from error
        _WRAPPED_CACHE.store(cache, response, cache_key, result)
        return result
