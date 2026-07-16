"""Stream report card (baseline-compared KPI scorecard) + full chat-log export endpoints."""

from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from fastapi.responses import StreamingResponse

from ....application.streams.export_query import iter_stream_export_rows, stream_exists
from ....application.streams.report_models import (
    StreamReport,
)
from ....application.streams.report_query import (
    StreamNotFoundError,
)
from ....application.streams.report_query import (
    get_stream_report as query_stream_report,
)
from ....logging_config import get_logger
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy
from ...composition import STREAM_REPORT_SOURCES
from ...dependencies import get_cache
from ...security.auth import get_current_user
from ...security.auth_models import UserInDB
from ...security.rate_limiter import limiter, rate_limits
from ...transport.export_utils import iter_csv, iter_ndjson
from ...transport.models import ErrorResponse, RateLimitErrorResponse

logger = get_logger(__name__)

router = APIRouter(tags=["Streams"])

_REPORT_CACHE = ModelCachePolicy("stream_report", CacheTTL.STREAM_ANALYTICS, StreamReport)


@router.get(
    "/streams/{stream_id}/report",
    response_model=StreamReport,
    summary="Get the report card for a stream",
    description=(
        "KPI scorecard for one stream, compared against the creator's previous rolled-up "
        "streams (delta vs baseline median + percentile rank)."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Stream not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_stream_report(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1}),
    lookback: int = Query(10, ge=2, le=30, description="Previous streams to use as baseline"),
) -> StreamReport:
    """Build the report card for a single stream.

    404 only when the stream row itself does not exist. An un-rolled-up stream returns
    200 with all metric values None (nullable = unknown, never coalesced to 0). Baseline
    math uses only previous rolled-up streams; with fewer than 2 of them every
    delta_pct/percentile/baseline_median is None.
    """
    with _REPORT_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _REPORT_CACHE.lookup(cache, response, stream_id, lookback)
        if cached_result is not None:
            return cached_result

        try:
            result = query_stream_report(stream_id, lookback, STREAM_REPORT_SOURCES)
        except StreamNotFoundError as error:
            raise HTTPException(status_code=404, detail="Stream not found") from error
        _REPORT_CACHE.store(cache, response, cache_key, result)
        return result


_EXPORT_FIELDNAMES = ["id", "time", "chatter_id", "nick", "text", "is_subscriber", "badges"]


@router.get(
    "/streams/{stream_id}/export",
    summary="Export the full chat log for a stream",
    description="Streams every chat message of a stream as NDJSON or CSV. Requires authentication.",
    responses={
        401: {"description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Stream not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.HEAVY)
def export_stream_chat(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1}),
    format: str = Query("ndjson", pattern="^(ndjson|csv)$", description="Export format"),
    current_user: UserInDB = Depends(get_current_user),
) -> StreamingResponse:
    """Stream the full chat log. Never cached; row keys match the /messages replay endpoint."""
    # 404 must be decided BEFORE streaming starts — the status is immutable afterwards.
    if not stream_exists(stream_id):
        raise HTTPException(status_code=404, detail="Stream not found")

    rows = iter_stream_export_rows(stream_id, getattr(request.app.state, "database_pool", None))
    if format == "csv":
        content: Iterator[str] = iter_csv(_EXPORT_FIELDNAMES, rows)
        media_type, extension = "text/csv", "csv"
    else:
        content = iter_ndjson(rows)
        media_type, extension = "application/x-ndjson", "ndjson"

    return StreamingResponse(
        content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="stream_{stream_id}_chat.{extension}"'},
    )
