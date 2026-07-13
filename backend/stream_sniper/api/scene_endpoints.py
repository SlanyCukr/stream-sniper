"""Read-only scene endpoints: live-now dashboard, creator leaderboard, copypasta library.

All three are public (no auth), following the analytics/community endpoint conventions:
sync `def` handlers (psycopg2 blocks), `request: Request` + `response: Response` for slowapi,
in-process TTL cache keyed on the query params, nullable = unknown (never coalesce NULL -> 0).
"""

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response

from ..database.scene_table_gateway import (
    select_scene_leaderboard_db,
    select_scene_peak_viewers_db,
)
from ..database.stream_copypasta_stats_table_gateway import (
    select_copypasta_context_db,
    select_copypasta_propagation_db,
    select_scene_copypastas_db,
)
from ..database.stream_viewer_sample_table_gateway import (
    select_latest_sample_time_db,
    select_live_now_db,
)
from ..logging_config import get_logger
from .cache import CacheTTL, get_cache
from .models import ErrorResponse
from .monitoring import record_cache_operation
from .rate_limiter import limiter, rate_limits
from .scene_models import (
    Copypasta,
    CopypastaContextMessage,
    CopypastaOccurrence,
    CopypastaPropagation,
    LeaderboardEntry,
    LiveStreamer,
    SceneCopypastas,
    SceneLeaderboard,
    SceneLive,
)

logger = get_logger(__name__)

# Live data refreshes every ~5 min (one sample per streamer per live poll), so a short cache
# TTL keeps the dashboard fresh; the hour-scale STREAM_ANALYTICS TTL would be absurd here.
_LIVE_CACHE_TTL_SECONDS = 60

router = APIRouter(tags=["Scene"])


@router.get(
    "/scene/copypastas/{message_text_id}",
    response_model=CopypastaPropagation,
    summary="Get a copypasta propagation history",
    description="Every stream/channel where a copypasta appeared, plus context around its origin.",
    responses={
        404: {"model": ErrorResponse, "description": "Copypasta not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
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
    try:
        cache = get_cache()
        cache_key = cache._generate_key("copypasta_propagation", message_text_id, context_seconds)
        cached = cache.get(cache_key)
        if cached is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "copypasta_propagation")
            return CopypastaPropagation(**cached)

        record_cache_operation("miss", "copypasta_propagation")
        text, rows = select_copypasta_propagation_db(message_text_id)
        if text is None:
            raise HTTPException(status_code=404, detail="Copypasta not found")

        occurrences = [
            CopypastaOccurrence(
                stream_id=row[0],
                creator_id=row[1],
                nick=row[2],
                display_name=row[3],
                profile_image_url=row[4],
                stream_title=row[5],
                stream_start=row[6],
                first_seen=row[7],
                usage_count=row[8],
                chatter_count=row[9],
            )
            for row in rows
        ]
        first = next((item for item in occurrences if item.first_seen is not None), None)
        context_rows = (
            select_copypasta_context_db(first.stream_id, first.first_seen, context_seconds, 100)
            if first is not None
            else []
        )
        context = [
            CopypastaContextMessage(id=row[0], time=row[1], chatter_id=row[2], nick=row[3], text=row[4])
            for row in context_rows
        ]
        result = CopypastaPropagation(
            message_text_id=message_text_id,
            text=text,
            usage_count=sum(item.usage_count for item in occurrences),
            chatter_appearances=sum(item.chatter_count for item in occurrences),
            stream_count=len(occurrences),
            creator_count=len({item.creator_id for item in occurrences}),
            first_seen=first.first_seen if first else None,
            occurrences=occurrences,
            origin_context=context,
        )
        cache.set(cache_key, result.model_dump(), CacheTTL.STREAM_ANALYTICS)
        record_cache_operation("set", "copypasta_propagation")
        response.headers["X-Cache"] = "MISS"
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching copypasta propagation: {exc}")
        record_cache_operation("error", "copypasta_propagation")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/scene/live",
    response_model=SceneLive,
    summary="Get currently-live tracked streamers",
    description="Tracked streamers inferred live from fresh viewer samples, sorted by viewer count.",
    responses={429: {"model": ErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.GENERAL)
def get_scene_live(request: Request, response: Response) -> SceneLive:
    """Get the live-now dashboard: streamers with a viewer sample in the last 10 minutes."""
    try:
        cache = get_cache()
        cache_key = cache._generate_key("scene_live")
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "scene_live")
            return SceneLive(**cached_result)

        record_cache_operation("miss", "scene_live")
        rows = select_live_now_db()
        last_sample_at = select_latest_sample_time_db()

        live = [
            LiveStreamer(
                creator_id=row[0],
                nick=row[1],
                display_name=row[2],
                profile_image_url=row[3],
                viewer_count=row[4],
                title=row[5],
                session_started_at=row[6],
                sampled_at=row[7],
            )
            for row in rows
        ]
        live.sort(key=lambda s: s.viewer_count, reverse=True)

        result = SceneLive(live=live, live_count=len(live), last_sample_at=last_sample_at)
        cache.set(cache_key, result.model_dump(), _LIVE_CACHE_TTL_SECONDS)
        record_cache_operation("set", "scene_live")
        response.headers["X-Cache"] = "MISS"
        return result
    except Exception as exc:
        logger.error(f"Error fetching scene live: {exc}")
        record_cache_operation("error", "scene_live")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/scene/leaderboard",
    response_model=SceneLeaderboard,
    summary="Get the scene creator leaderboard",
    description="Creators ranked by total messages over a 7- or 30-day window.",
    responses={429: {"model": ErrorResponse, "description": "Rate limit exceeded"}},
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
    try:
        cache = get_cache()
        cache_key = cache._generate_key("scene_leaderboard", window)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "scene_leaderboard")
            return SceneLeaderboard(**cached_result)

        record_cache_operation("miss", "scene_leaderboard")
        rows = select_scene_leaderboard_db(window)
        peak_map = {row[0]: row[1] for row in select_scene_peak_viewers_db(window)}

        entries = [
            LeaderboardEntry(
                rank=rank,
                creator_id=row[0],
                nick=row[1],
                display_name=row[2],
                profile_image_url=row[3],
                streams=row[4],
                hours_streamed=row[5],
                total_messages=row[6],
                msgs_per_min=row[7],
                chatter_appearances=row[8],
                peak_viewers=peak_map.get(row[0]),
            )
            for rank, row in enumerate(rows, start=1)
        ]

        result = SceneLeaderboard(window_days=window, entries=entries)
        cache.set(cache_key, result.model_dump(), CacheTTL.STREAM_ANALYTICS)
        record_cache_operation("set", "scene_leaderboard")
        response.headers["X-Cache"] = "MISS"
        return result
    except Exception as exc:
        logger.error(f"Error fetching scene leaderboard: {exc}")
        record_cache_operation("error", "scene_leaderboard")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/scene/copypastas",
    response_model=SceneCopypastas,
    summary="Get the scene copypasta library",
    description="Deduplicated copypastas aggregated scene-wide, filterable by window and creator.",
    responses={429: {"model": ErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.ANALYTICS)
def get_scene_copypastas(
    request: Request,
    response: Response,
    days: Optional[int] = Query(None, ge=1, description="Window in days; omit for all-time"),
    creator_id: Optional[int] = Query(None, description="Restrict to one creator"),
    sort: Literal["usage", "spread", "recent"] = Query("usage", description="Sort order"),
    limit: int = Query(25, ge=1, le=100, description="Page size"),
    offset: int = Query(0, ge=0, description="Row offset for pagination"),
) -> SceneCopypastas:
    """Get a page of scene-wide copypastas, sorted by usage, channel spread, or recency."""
    try:
        cache = get_cache()
        cache_key = cache._generate_key("scene_copypastas", days, creator_id, sort, limit, offset)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "scene_copypastas")
            return SceneCopypastas(**cached_result)

        record_cache_operation("miss", "scene_copypastas")
        rows, total = select_scene_copypastas_db(days, creator_id, sort, limit, offset)

        items = [
            Copypasta(
                message_text_id=row[0],
                text=row[1],
                usage_count=row[2],
                chatter_appearances=row[3],
                stream_count=row[4],
                creator_count=row[5],
                first_seen=row[6],
                last_stream_start=row[7],
            )
            for row in rows
        ]

        result = SceneCopypastas(total=total, items=items)
        cache.set(cache_key, result.model_dump(), CacheTTL.STREAM_ANALYTICS)
        record_cache_operation("set", "scene_copypastas")
        response.headers["X-Cache"] = "MISS"
        return result
    except Exception as exc:
        logger.error(f"Error fetching scene copypastas: {exc}")
        record_cache_operation("error", "scene_copypastas")
        raise HTTPException(status_code=500, detail="Internal server error")
