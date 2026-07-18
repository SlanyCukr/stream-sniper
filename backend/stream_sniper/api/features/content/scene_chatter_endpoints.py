"""Public read endpoint for scene-wide chatter power rankings.

Public (no auth), following the analytics/scene endpoint conventions: sync `def`
handler (psycopg2 blocks), `request: Request` + `response: Response` for slowapi,
in-process TTL cache keyed on the query params plus the scene rollup version.
"""

from fastapi import APIRouter, HTTPException, Query, Request, Response

from ....database.gateways.creators.scene_chatter_rankings_gateway import (
    select_scene_chatter_rankings_db,
)
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy
from ...caching.rollup_version import scene_rollup_version
from ...dependencies import get_cache
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import ErrorOrValidationResponse, RateLimitErrorResponse
from .scene_chatter_models import RankItem, SceneChatterRankings

router = APIRouter(tags=["Scene"])

# window selector -> trailing-window length in days (None = all-time aggregate).
_WINDOWS: dict[str, int | None] = {"all": None, "7": 7, "30": 30}

_RANKINGS_CACHE = ModelCachePolicy("scene_chatter_rankings", CacheTTL.STREAM_ANALYTICS, SceneChatterRankings)


@router.get(
    "/scene/chatter-rankings",
    response_model=SceneChatterRankings,
    summary="Get the scene chatter power rankings",
    description=(
        "Chatters ranked by total messages, all-time or over a trailing 7- or 30-day window. "
        "Bots are excluded. Each entry carries the chatter's home channel (the creator they chat "
        "in most) and its message share. Paginated, most messages first."
    ),
    responses={
        422: {"model": ErrorOrValidationResponse, "description": "Invalid window or query parameter"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_scene_chatter_rankings(
    request: Request,
    response: Response,
    window: str = Query("all", description="Window selector: 'all', '7', or '30'"),
    limit: int = Query(50, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Row offset for pagination"),
) -> SceneChatterRankings:
    """Get a page of the scene-wide chatter leaderboard for the requested window."""
    # Validate before the try so an unknown window 422s (not 500). A Literal query
    # param would 422 for free, but a plain-language message reads better here.
    if window not in _WINDOWS:
        raise HTTPException(status_code=422, detail="window must be 'all', '7', or '30'.")

    with _RANKINGS_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached = _RANKINGS_CACHE.lookup(
            cache, response, window, limit, offset, scene_rollup_version()
        )
        if cached is not None:
            return cached

        rows, has_more = select_scene_chatter_rankings_db(_WINDOWS[window], limit, offset)
        items = [RankItem.from_row(row, rank=offset + index + 1) for index, row in enumerate(rows)]
        result = SceneChatterRankings(window=window, items=items, has_more=has_more)
        _RANKINGS_CACHE.store(cache, response, cache_key, result)
        return result
