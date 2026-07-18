"""Public read endpoint for the Scene Wrapped period recap.

Public (no auth), following the analytics/scene endpoint conventions: sync ``def``
handler (psycopg2 blocks), ``request: Request`` + ``response: Response`` for slowapi,
in-process TTL cache keyed on the window plus the scene rollup version, nullable =
unknown (an un-rolled msgs_per_min or a sample-less peak_viewers is never coalesced to
0). The multi-gateway assembly lives in ``application/scenes/wrapped_query``; this
handler owns only HTTP + caching. The module-level ``router`` name is kept so api.py's
registration stays valid.
"""

from fastapi import APIRouter, Query, Request, Response

from ....application.scenes.wrapped_models import SceneWrapped
from ....application.scenes.wrapped_query import get_scene_wrapped
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy
from ...caching.rollup_version import scene_rollup_version
from ...dependencies import get_cache
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import ErrorOrValidationResponse, RateLimitErrorResponse

router = APIRouter(tags=["Scene"])

_WRAPPED_CACHE = ModelCachePolicy("scene_wrapped", CacheTTL.STREAM_ANALYTICS, SceneWrapped)


@router.get(
    "/scene/wrapped",
    response_model=SceneWrapped,
    summary="Get the Scene Wrapped period recap",
    description="A scene-wide recap over a trailing window: totals plus top creators, chatters, moments, "
    "copypastas, emotes, and notable events.",
    responses={
        422: {"model": ErrorOrValidationResponse, "description": "Invalid window parameter"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_scene_wrapped_endpoint(
    request: Request,
    response: Response,
    days: int = Query(30, ge=7, le=90, description="Recap window length in days (7-90)"),
) -> SceneWrapped:
    """Get the Scene Wrapped recap for the trailing ``days`` window."""
    with _WRAPPED_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached = _WRAPPED_CACHE.lookup(cache, response, days, scene_rollup_version())
        if cached is not None:
            return cached

        result = get_scene_wrapped(days)
        _WRAPPED_CACHE.store(cache, response, cache_key, result)
        return result
