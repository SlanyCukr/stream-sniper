"""Public read endpoints for scene-wide trending emotes and copypastas (velocity).

Both are public (no auth), following the analytics/scene endpoint conventions:
sync ``def`` handlers (psycopg2 blocks), ``request: Request`` + ``response: Response`` for
slowapi, in-process TTL cache keyed on the query params plus the scene rollup version, and
plain-language 422 copy for an out-of-range window.
"""

from fastapi import APIRouter, HTTPException, Query, Request, Response

from ....database.gateways.analytics.scene_trends_gateway import (
    select_trending_copypastas_db,
    select_trending_emotes_db,
)
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy
from ...caching.rollup_version import scene_rollup_version
from ...dependencies import get_cache
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import ErrorOrValidationResponse, RateLimitErrorResponse
from .scene_trending_models import (
    TrendingCopypasta,
    TrendingCopypastas,
    TrendingEmote,
    TrendingEmotes,
)

# Velocity compares two equal-length windows; only these lengths are offered so the
# "prior" window is always a clean, comparable baseline.
_ALLOWED_WINDOWS = (7, 14, 30)

router = APIRouter(tags=["Scene"])

_COPYPASTAS_CACHE = ModelCachePolicy("scene_trending_copypastas", CacheTTL.STREAM_ANALYTICS, TrendingCopypastas)
_EMOTES_CACHE = ModelCachePolicy("scene_trending_emotes", CacheTTL.STREAM_ANALYTICS, TrendingEmotes)


def _validate_window(window: int) -> None:
    """Reject an unsupported window with a plain-language 422 (before the cache/query)."""
    if window not in _ALLOWED_WINDOWS:
        raise HTTPException(status_code=422, detail="window must be 7, 14, or 30 days")


@router.get(
    "/scene/trending/copypastas",
    response_model=TrendingCopypastas,
    summary="Get trending copypastas (velocity)",
    description="Copypastas rising, falling, or new in the scene: current window vs the prior window.",
    responses={
        422: {"model": ErrorOrValidationResponse, "description": "Invalid window or query parameter"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_trending_copypastas(
    request: Request,
    response: Response,
    window: int = Query(7, description="Window length in days (7, 14, or 30)"),
    creator_id: int | None = Query(None, ge=1, description="Restrict to one creator"),
    limit: int = Query(20, ge=1, le=50, description="Maximum items to return"),
) -> TrendingCopypastas:
    """Scene-wide copypasta velocity: what is rising/falling/new over the chosen window."""
    _validate_window(window)
    with _COPYPASTAS_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached = _COPYPASTAS_CACHE.lookup(
            cache, response, window, creator_id if creator_id is not None else "all", limit, scene_rollup_version()
        )
        if cached is not None:
            return cached

        rows = select_trending_copypastas_db(window, creator_id, limit)
        result = TrendingCopypastas(window=window, items=[TrendingCopypasta.from_row(row) for row in rows])
        _COPYPASTAS_CACHE.store(cache, response, cache_key, result)
        return result


@router.get(
    "/scene/trending/emotes",
    response_model=TrendingEmotes,
    summary="Get trending emotes (velocity)",
    description="Emotes rising, falling, or new in the scene: current window vs the prior window.",
    responses={
        422: {"model": ErrorOrValidationResponse, "description": "Invalid window or query parameter"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_trending_emotes(
    request: Request,
    response: Response,
    window: int = Query(7, description="Window length in days (7, 14, or 30)"),
    creator_id: int | None = Query(None, ge=1, description="Restrict to one creator"),
    limit: int = Query(20, ge=1, le=50, description="Maximum items to return"),
) -> TrendingEmotes:
    """Scene-wide emote velocity: what is rising/falling/new over the chosen window."""
    _validate_window(window)
    with _EMOTES_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached = _EMOTES_CACHE.lookup(
            cache, response, window, creator_id if creator_id is not None else "all", limit, scene_rollup_version()
        )
        if cached is not None:
            return cached

        rows = select_trending_emotes_db(window, creator_id, limit)
        result = TrendingEmotes(window=window, items=[TrendingEmote.from_row(row) for row in rows])
        _EMOTES_CACHE.store(cache, response, cache_key, result)
        return result
