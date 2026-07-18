"""Public read endpoint for the scene-wide Highlights Wall (hype-ranked moments).

Public (no auth), following the analytics/scene endpoint conventions: sync `def` handler
(psycopg2 blocks), `request: Request` + `response: Response` for slowapi, in-process TTL
cache keyed on the query params + scene rollup version, nullable = unknown (a NULL ratio /
share is never coalesced to 0). The module-level ``router`` name is kept so api.py's
registration stays valid.
"""

from typing import Literal

from fastapi import APIRouter, Query, Request, Response

from ....database.gateways.content.scene_highlights_gateway import select_scene_highlights_db
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy
from ...caching.rollup_version import scene_rollup_version
from ...dependencies import get_cache
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import ErrorOrValidationResponse, RateLimitErrorResponse
from .scene_highlights_models import Highlight, HighlightsResponse

router = APIRouter(tags=["Scene"])

_HIGHLIGHTS_CACHE = ModelCachePolicy("scene_highlights", CacheTTL.STREAM_ANALYTICS, HighlightsResponse)


@router.get(
    "/scene/highlights",
    response_model=HighlightsResponse,
    summary="Get the scene-wide Highlights Wall",
    description="Hype- or recency-ranked chat moments across every tracked creator, minus rejected ones.",
    responses={
        422: {"model": ErrorOrValidationResponse, "description": "Invalid window, sort, or query parameter"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_scene_highlights(
    request: Request,
    response: Response,
    window: Literal["all", "7", "30"] = Query("all", description="Time window in days, or all-time"),
    creator_id: int | None = Query(None, ge=1, description="Restrict to one creator"),
    sort: Literal["hype", "recent"] = Query("hype", description="Order by spike ratio or recency"),
    limit: int = Query(24, ge=1, le=50, description="Page size"),
    offset: int = Query(0, ge=0, description="Row offset for pagination"),
) -> HighlightsResponse:
    """Get a page of the scene-wide Highlights Wall, hype- or recency-ranked."""
    window_days = None if window == "all" else int(window)
    with _HIGHLIGHTS_CACHE.record_failures():
        cache = get_cache(request)
        # "all" (not 0/None) for the unscoped creator so no real creator id can collide.
        cache_key, cached = _HIGHLIGHTS_CACHE.lookup(
            cache,
            response,
            window,
            creator_id if creator_id is not None else "all",
            sort,
            limit,
            offset,
            scene_rollup_version(),
        )
        if cached is not None:
            return cached

        rows, has_more = select_scene_highlights_db(window_days, creator_id, sort, limit, offset)
        items = [
            Highlight(
                stream_id=row.stream_id,
                stream_title=row.stream_title,
                twitch_id=str(row.twitch_id) if row.twitch_id is not None else None,
                creator_id=row.creator_id,
                creator_nick=row.creator_nick,
                creator_display_name=row.creator_display_name,
                bucket_minute=row.bucket_minute,
                offset_seconds=row.offset_seconds,
                ratio=row.ratio,
                message_count=row.message_count,
                unique_chatters=row.unique_chatters,
                sub_share=row.sub_share,
                emote_share=row.emote_share,
                top_phrases=row.top_phrases,
                sample_messages=row.sample_messages,
                clip_url=row.clip_url,
                review_status=row.review_status,
            )
            for row in rows
        ]
        result = HighlightsResponse(window=window, sort=sort, items=items, has_more=has_more)
        _HIGHLIGHTS_CACHE.store(cache, response, cache_key, result)
        return result
