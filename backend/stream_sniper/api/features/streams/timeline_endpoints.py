"""Read-only endpoint for per-stream timeline analytics (KPI tiles + chart + moments)."""

from fastapi import APIRouter, Path, Request, Response

from ....application.streams.timeline_models import StreamTimeline
from ....application.streams.timeline_query import get_stream_timeline as query_stream_timeline
from ....logging_config import get_logger
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy
from ...composition import STREAM_TIMELINE_SOURCES
from ...dependencies import get_cache
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import RateLimitErrorResponse

logger = get_logger(__name__)

router = APIRouter(tags=["Streams"])

_TIMELINE_CACHE = ModelCachePolicy("stream_timeline", CacheTTL.STREAM_ANALYTICS, StreamTimeline)


@router.get(
    "/streams/{stream_id}/timeline",
    response_model=StreamTimeline,
    summary="Get stream timeline analytics",
    description="Per-minute message buckets, spike moments, and KPI metrics for one stream.",
    responses={
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_stream_timeline(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1}),
) -> StreamTimeline:
    """Get the timeline (buckets + moments + KPI metrics) for a single stream.

    Buckets are returned as a gap-free per-minute grid. Moments come from persisted enriched
    rows (stream_moment) when the stream has been rolled up under 0008; otherwise they fall
    back to live spike detection with the enrichment fields left None. An un-rolled-up stream
    (no `stream_metrics` / `stream_time_bucket` rows) returns 200 with empty `buckets`/`moments`
    and `metrics=None` — never 404.
    """
    with _TIMELINE_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _TIMELINE_CACHE.lookup(cache, response, stream_id)
        if cached_result is not None:
            return cached_result

        result = query_stream_timeline(stream_id, STREAM_TIMELINE_SOURCES)
        _TIMELINE_CACHE.store(cache, response, cache_key, result)
        return result
