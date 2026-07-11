"""Read-only endpoints for creator-level analytics (trends and regulars)."""

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response

from ..database.creator_chatter_stats_table_gateway import select_creator_regulars_db
from ..database.stream_metrics_table_gateway import select_creator_metrics_series_db
from ..database.stream_table_gateway import select_all_stream_count_db
from ..logging_config import get_logger
from .analytics_models import CreatorRegulars, CreatorTrends, Regular, TrendPoint
from .cache import CacheTTL, get_cache
from .models import ErrorResponse
from .monitoring import record_cache_operation
from .rate_limiter import limiter, rate_limits

logger = get_logger(__name__)

router = APIRouter(tags=["Creators"])


@router.get(
    "/creator/{creator_id}/trends",
    response_model=CreatorTrends,
    summary="Get a creator's recent stream trends",
    description="Return per-stream metrics for a creator's most recent streams, ascending by start.",
    responses={
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
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
    try:
        cache = get_cache()
        cache_key = cache._generate_key("creator_trends", creator_id, limit)
        cached_rows = cache.get(cache_key)

        if cached_rows is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "creator_trends")
            rows = cached_rows
        else:
            record_cache_operation("miss", "creator_trends")
            rows = select_creator_metrics_series_db(creator_id, limit)
            cache.set(cache_key, rows, CacheTTL.STREAM_ANALYTICS)
            record_cache_operation("set", "creator_trends")
            response.headers["X-Cache"] = "MISS"

        points = [
            TrendPoint(
                stream_id=row[0],
                title=row[1],
                start=row[2],
                duration_seconds=row[3],
                message_count=row[4],
                messages_per_minute=row[5],
                unique_chatters=row[6],
                new_chatters=row[7],
                returning_chatters=row[8],
            )
            for row in rows
        ]
        return CreatorTrends(creator_id=creator_id, points=points)
    except Exception as exc:
        logger.error(f"Error fetching creator trends: {exc}")
        record_cache_operation("error", "creator_trends")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/creator/{creator_id}/regulars",
    response_model=CreatorRegulars,
    summary="Get a creator's recurring chatters",
    description="Return recurring chatters for a creator, ranked by attendance, with attendance rate.",
    responses={
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
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
) -> CreatorRegulars:
    """Get a creator's recurring chatters with attendance rates."""
    try:
        cache = get_cache()

        count_cache_key = cache._generate_key("creator_stream_count", creator_id)
        cached_count = cache.get(count_cache_key)
        regulars_cache_key = cache._generate_key(
            "creator_regulars", creator_id, sort, dir, min_streams, limit
        )
        cached_regulars = cache.get(regulars_cache_key)
        count_from_cache = cached_count is not None
        regulars_from_cache = cached_regulars is not None

        if count_from_cache:
            record_cache_operation("hit", "creator_stream_count")
            total_streams = cached_count
        else:
            record_cache_operation("miss", "creator_stream_count")
            total_streams = select_all_stream_count_db(creator_id)
            cache.set(count_cache_key, total_streams, CacheTTL.STREAM_DETAILS)
            record_cache_operation("set", "creator_stream_count")

        if regulars_from_cache:
            record_cache_operation("hit", "creator_regulars")
            rows = cached_regulars
        else:
            record_cache_operation("miss", "creator_regulars")
            rows = select_creator_regulars_db(creator_id, min_streams, limit, sort=sort, dir=dir)
            cache.set(regulars_cache_key, rows, CacheTTL.STREAM_DETAILS)
            record_cache_operation("set", "creator_regulars")

        if count_from_cache and regulars_from_cache:
            response.headers["X-Cache"] = "HIT"
        elif count_from_cache or regulars_from_cache:
            response.headers["X-Cache"] = "PARTIAL"
        else:
            response.headers["X-Cache"] = "MISS"

        regulars = [
            Regular(
                chatter_id=row[0],
                nick=row[1],
                streams_attended=row[2],
                attendance_rate=(round(row[2] / total_streams, 4) if total_streams else 0.0),
                first_seen=row[3],
                last_seen=row[4],
                last_stream_attended=row[5],
                message_count=row[6],
            )
            for row in rows
        ]
        return CreatorRegulars(creator_id=creator_id, total_streams=total_streams, regulars=regulars)
    except Exception as exc:
        logger.error(f"Error fetching creator regulars: {exc}")
        record_cache_operation("error", "creator_regulars")
        raise HTTPException(status_code=500, detail="Internal server error")
