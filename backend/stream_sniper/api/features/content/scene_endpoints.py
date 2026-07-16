"""Read-only scene endpoints: live-now dashboard, creator leaderboard, copypasta library.

All three are public (no auth), following the analytics/community endpoint conventions:
sync `def` handlers (psycopg2 blocks), `request: Request` + `response: Response` for slowapi,
in-process TTL cache keyed on the query params, nullable = unknown (never coalesce NULL -> 0).
"""

from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request, Response

from ....application.scenes.models import CopypastaPropagation, SceneCopypastas, SceneLeaderboard, SceneLive
from ....application.scenes.scene_query import (
    CopypastaNotFoundError,
)
from ....application.scenes.scene_query import (
    get_copypasta_propagation as query_copypasta_propagation,
)
from ....application.scenes.scene_query import (
    get_scene_copypastas as query_scene_copypastas,
)
from ....application.scenes.scene_query import (
    get_scene_leaderboard as query_scene_leaderboard,
)
from ....application.scenes.scene_query import (
    get_scene_live as query_scene_live,
)
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy
from ...dependencies import get_cache
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import ErrorOrValidationResponse, ErrorResponse, RateLimitErrorResponse

# Live data refreshes every ~5 min (one sample per streamer per live poll), so a short cache
# TTL keeps the dashboard fresh; the hour-scale STREAM_ANALYTICS TTL would be absurd here.
_LIVE_CACHE_TTL_SECONDS = 60

router = APIRouter(tags=["Scene"])

_PROPAGATION_CACHE = ModelCachePolicy("copypasta_propagation", CacheTTL.STREAM_ANALYTICS, CopypastaPropagation)
_LIVE_CACHE = ModelCachePolicy("scene_live", _LIVE_CACHE_TTL_SECONDS, SceneLive)
_LEADERBOARD_CACHE = ModelCachePolicy("scene_leaderboard", CacheTTL.STREAM_ANALYTICS, SceneLeaderboard)
_COPYPASTAS_CACHE = ModelCachePolicy("scene_copypastas", CacheTTL.STREAM_ANALYTICS, SceneCopypastas)


@router.get(
    "/scene/copypastas/{message_text_id}",
    response_model=CopypastaPropagation,
    summary="Get a copypasta propagation history",
    description="Every stream/channel where a copypasta appeared, plus context around its origin.",
    responses={
        404: {"model": ErrorResponse, "description": "Copypasta not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_copypasta_propagation(
    request: Request,
    response: Response,
    message_text_id: int,
    context_seconds: int = Query(90, ge=15, le=300),
) -> CopypastaPropagation:
    """Return the complete bounded-rollup propagation path for one message text."""
    with _PROPAGATION_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached = _PROPAGATION_CACHE.lookup(cache, response, message_text_id, context_seconds)
        if cached is not None:
            return cached
        try:
            result = query_copypasta_propagation(message_text_id, context_seconds)
        except CopypastaNotFoundError as error:
            raise HTTPException(status_code=404, detail="Copypasta not found") from error
        _PROPAGATION_CACHE.store(cache, response, cache_key, result)
        return result


@router.get(
    "/scene/live",
    response_model=SceneLive,
    summary="Get currently-live tracked streamers",
    description="Tracked streamers inferred live from fresh viewer samples, sorted by viewer count.",
    responses={429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.GENERAL)
def get_scene_live(request: Request, response: Response) -> SceneLive:
    """Get the live-now dashboard: streamers with a viewer sample in the last 10 minutes."""
    with _LIVE_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _LIVE_CACHE.lookup(cache, response)
        if cached_result is not None:
            return cached_result

        result = query_scene_live()
        _LIVE_CACHE.store(cache, response, cache_key, result)
        return result


@router.get(
    "/scene/leaderboard",
    response_model=SceneLeaderboard,
    summary="Get the scene creator leaderboard",
    description="Creators ranked by total messages over a 7- or 30-day window.",
    responses={
        422: {"model": ErrorOrValidationResponse, "description": "Invalid leaderboard window or query parameter"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_scene_leaderboard(
    request: Request,
    response: Response,
    window: int = Query(7, description="Window length in days (7 or 30)"),
) -> SceneLeaderboard:
    """Get the scene-wide creator leaderboard for the window (ranked by total messages)."""
    # Only two windows are supported; validate before the try so it 422s (not 500). A Literal[7, 30]
    # query param would 422 for free, but this FastAPI version won't coerce the "30" string to int.
    if window not in (7, 30):
        raise HTTPException(status_code=422, detail="window must be 7 or 30")
    with _LEADERBOARD_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _LEADERBOARD_CACHE.lookup(cache, response, window)
        if cached_result is not None:
            return cached_result

        result = query_scene_leaderboard(window)
        _LEADERBOARD_CACHE.store(cache, response, cache_key, result)
        return result


@router.get(
    "/scene/copypastas",
    response_model=SceneCopypastas,
    summary="Get the scene copypasta library",
    description="Deduplicated copypastas aggregated scene-wide, filterable by window and creator.",
    responses={429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.ANALYTICS)
def get_scene_copypastas(
    request: Request,
    response: Response,
    days: int | None = Query(None, ge=1, description="Window in days; omit for all-time"),
    creator_id: int | None = Query(None, description="Restrict to one creator"),
    sort: Literal["usage", "spread", "recent"] = Query("usage", description="Sort order"),
    limit: int = Query(25, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Row offset for pagination"),
) -> SceneCopypastas:
    """Get a page of scene-wide copypastas, sorted by usage, channel spread, or recency."""
    with _COPYPASTAS_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _COPYPASTAS_CACHE.lookup(cache, response, days, creator_id, sort, limit, offset)
        if cached_result is not None:
            return cached_result

        result = query_scene_copypastas(days, creator_id, sort, limit, offset)
        _COPYPASTAS_CACHE.store(cache, response, cache_key, result)
        return result
