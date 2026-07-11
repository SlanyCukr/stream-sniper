"""Read-only endpoint for per-stream timeline analytics (KPI tiles + chart + moments)."""

from datetime import datetime, timedelta
from typing import Any, List, cast

from fastapi import APIRouter, HTTPException, Path, Request, Response

from ..analytics.moments import detect_moments
from ..database.stream_metrics_table_gateway import (
    select_stream_header_db,
    select_stream_metrics_db,
)
from ..database.stream_moment_table_gateway import select_stream_moments_db
from ..database.stream_time_bucket_table_gateway import select_stream_buckets_db
from ..database.stream_viewer_sample_table_gateway import select_stream_viewer_samples_db
from ..logging_config import get_logger
from .cache import CacheTTL, get_cache
from .models import ErrorResponse
from .monitoring import record_cache_operation
from .rate_limiter import limiter, rate_limits
from .timeline_models import (
    StreamTimeline,
    TimelineBucket,
    TimelineMetrics,
    TimelineMoment,
    ViewerSample,
)

logger = get_logger(__name__)

router = APIRouter(tags=["Streams"])

_FMT = "%Y-%m-%dT%H:%M:%S"


def _zero_filled_buckets(bucket_rows) -> List[TimelineBucket]:
    """Expand the observed buckets into a gap-free per-minute grid (first..last observed).

    Synthesized minutes carry message/unique counts of 0 and sub/emote counts of None
    (unknown, not a real 0) so the frontend viewer overlay can align on a linear time axis.
    """
    if not bucket_rows:
        return []

    observed = {
        row[0]: TimelineBucket(
            bucket_minute=row[0],
            message_count=row[1],
            unique_chatters=row[2],
            sub_messages=row[3],
            emote_messages=row[4],
        )
        for row in bucket_rows
    }
    first = datetime.strptime(bucket_rows[0][0], _FMT)
    last = datetime.strptime(bucket_rows[-1][0], _FMT)

    buckets: List[TimelineBucket] = []
    cursor = first
    while cursor <= last:
        key = cursor.strftime(_FMT)
        buckets.append(
            observed.get(
                key,
                TimelineBucket(bucket_minute=key, message_count=0, unique_chatters=0),
            )
        )
        cursor += timedelta(minutes=1)
    return buckets


def _persisted_moments(moment_rows) -> List[TimelineMoment]:
    """Build enriched moments from persisted stream_moment rows (see select_stream_moments_db)."""
    return [
        TimelineMoment(
            bucket_minute=row[0],
            offset_seconds=row[1],
            message_count=row[2],
            baseline=row[3],
            ratio=row[4],
            unique_chatters=row[5],
            sub_share=row[6],
            emote_share=row[7],
            top_phrases=row[8],
            sample_messages=row[9],
            status=row[10],
        )
        for row in moment_rows
    ]


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

    Buckets are returned as a gap-free per-minute grid. Moments come from persisted enriched
    rows (stream_moment) when the stream has been rolled up under 0008; otherwise they fall
    back to live spike detection with the enrichment fields left None. An un-rolled-up stream
    (no `stream_metrics` / `stream_time_bucket` rows) returns 200 with empty `buckets`/`moments`
    and `metrics=None` — never 404.
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
        moment_rows = select_stream_moments_db(stream_id)
        sample_rows = select_stream_viewer_samples_db(stream_id)

        stream_start = header_row[0] if header_row else None
        twitch_id = header_row[1] if header_row else None

        buckets = _zero_filled_buckets(bucket_rows)
        moments = (
            _persisted_moments(moment_rows)
            if moment_rows
            else detect_moments(bucket_rows, stream_start)
        )

        viewer_samples = [ViewerSample(t=row[0], viewer_count=row[1]) for row in sample_rows]
        peak_viewers = max((s.viewer_count for s in viewer_samples), default=None)

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
                sub_messages=metrics_row[8],
                emote_messages=metrics_row[9],
            )

        result = StreamTimeline(
            stream_id=stream_id,
            stream_start=stream_start,
            twitch_id=twitch_id,
            bucket_seconds=60,
            buckets=buckets,
            moments=moments,
            metrics=metrics,
            viewer_samples=viewer_samples,
            peak_viewers=peak_viewers,
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
