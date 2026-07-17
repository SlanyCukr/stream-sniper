"""Compare two to four streams using existing bounded analytics rollups."""

from fastapi import APIRouter, HTTPException, Query, Request, Response

from ....application.streams.compare_models import StreamComparison
from ....application.streams.compare_query import (
    StreamComparisonNotFoundError,
    get_stream_comparison,
)
from ....logging_config import get_logger
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy
from ...caching.rollup_version import stream_rollup_version
from ...dependencies import get_cache
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import ErrorOrValidationResponse, ErrorResponse, RateLimitErrorResponse

logger = get_logger(__name__)
router = APIRouter(tags=["Streams"])
_STREAM_COMPARE_CACHE = ModelCachePolicy("stream_compare", CacheTTL.STREAM_ANALYTICS, StreamComparison)


@router.get(
    "/streams/compare",
    response_model=StreamComparison,
    summary="Compare two to four streams",
    responses={
        404: {"model": ErrorResponse, "description": "One or more streams not found"},
        422: {"model": ErrorOrValidationResponse, "description": "Invalid stream IDs"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.HEAVY)
def compare_streams(
    request: Request,
    response: Response,
    stream_ids: list[int] = Query(..., min_length=2, max_length=4),
) -> StreamComparison:
    if len(set(stream_ids)) != len(stream_ids):
        raise HTTPException(status_code=422, detail="stream_ids must be unique")
    with _STREAM_COMPARE_CACHE.record_failures():
        cache = get_cache(request)
        key, cached = _STREAM_COMPARE_CACHE.lookup(
            cache, response, *stream_ids, *(stream_rollup_version(stream_id) for stream_id in stream_ids)
        )
        if cached is not None:
            return cached

        try:
            result = get_stream_comparison(stream_ids)
        except StreamComparisonNotFoundError:
            raise HTTPException(status_code=404, detail="One or more streams not found")
        _STREAM_COMPARE_CACHE.store(cache, response, key, result)
        return result
