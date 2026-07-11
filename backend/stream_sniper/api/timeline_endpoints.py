"""Read-only endpoint for per-stream timeline analytics (KPI tiles + chart + moments)."""

from typing import Any, cast

from fastapi import APIRouter, HTTPException, Path, Request, Response

from ..database.stream_metrics_table_gateway import (
    select_stream_header_db,
    select_stream_metrics_db,
)
from ..database.stream_time_bucket_table_gateway import select_stream_buckets_db
from ..logging_config import get_logger
from .cache import CacheTTL, get_cache
from .models import ErrorResponse
from .moments import detect_moments
from .monitoring import record_cache_operation
from .rate_limiter import limiter, rate_limits
from .timeline_models import StreamTimeline, TimelineBucket, TimelineMetrics

logger = get_logger(__name__)

router = APIRouter(tags=["Streams"])


@router.get(
    "/stream/{stream_id}/timeline",
    response_model=StreamTimeline,
    summary="Get stream timeline analytics",
    description="Per-minute message buckets, spike moments, and KPI metrics for one stream.",
    responses={
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_stream_timeline(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1}),
) -> dict[str, Any]:
    """Get the timeline (buckets + moments + KPI metrics) for a single stream.

    An un-rolled-up stream (no `stream_metrics` / `stream_time_bucket` rows) returns 200 with
    empty `buckets`/`moments` and `metrics=None` — never 404.
    """
    try:
        cache = get_cache()
        cache_key = cache._generate_key("stream_timeline", stream_id)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "stream_timeline")
            return cast(dict[str, Any], cached_result)

        record_cache_operation("miss", "stream_timeline")
        bucket_rows = select_stream_buckets_db(stream_id)
        metrics_row = select_stream_metrics_db(stream_id)
        header_row = select_stream_header_db(stream_id)

        stream_start = header_row[0] if header_row else None
        twitch_id = header_row[1] if header_row else None

        buckets = [
            TimelineBucket(bucket_minute=row[0], message_count=row[1], unique_chatters=row[2])
            for row in bucket_rows
        ]
        moments = detect_moments(bucket_rows, stream_start)

        metrics = None
        if metrics_row is not None:
            metrics = TimelineMetrics(
                total_messages=metrics_row[0],
                unique_chatters=metrics_row[1],
                duration_seconds=metrics_row[2],
                messages_per_minute=metrics_row[3],
                peak_messages=metrics_row[4],
                peak_bucket_minute=metrics_row[5],
                new_chatters=metrics_row[6],
                returning_chatters=metrics_row[7],
            )

        result = StreamTimeline(
            stream_id=stream_id,
            stream_start=stream_start,
            twitch_id=twitch_id,
            bucket_seconds=60,
            buckets=buckets,
            moments=moments,
            metrics=metrics,
        )
        payload = result.model_dump()
        cache.set(cache_key, payload, CacheTTL.STREAM_ANALYTICS)
        record_cache_operation("set", "stream_timeline")
        response.headers["X-Cache"] = "MISS"
        return payload
    except Exception as exc:
        logger.error(f"Error fetching stream timeline: {exc}")
        record_cache_operation("error", "stream_timeline")
        raise HTTPException(status_code=500, detail="Internal server error")
