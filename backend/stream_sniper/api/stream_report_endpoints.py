"""Stream report card (baseline-compared KPI scorecard) + full chat-log export endpoints."""

from typing import Any, Iterator, List, Optional, cast
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from fastapi.responses import StreamingResponse

from ..analytics.report_stats import build_metric
from ..database.connection_pool import get_pool
from ..database.stream_emote_stats_table_gateway import select_stream_emotes_db
from ..database.stream_metrics_table_gateway import (
    select_creator_report_series_db,
    select_stream_metrics_db,
)
from ..database.stream_moment_table_gateway import select_stream_moments_db
from ..database.stream_phrase_stats_table_gateway import select_stream_phrases_db
from ..database.stream_table_gateway import select_stream_comprehensive_db
from ..database.stream_viewer_sample_table_gateway import select_stream_viewer_samples_db
from ..logging_config import get_logger
from .auth import UserInDB, get_current_user
from .cache import CacheTTL, get_cache
from .export_utils import iter_csv, iter_ndjson
from .models import ErrorResponse
from .monitoring import record_cache_operation
from .rate_limiter import limiter, rate_limits
from .stream_report_models import (
    ReportMetric,
    ReportMetrics,
    ReportMoment,
    StreamReport,
    TopEmote,
    TopPhrase,
)

logger = get_logger(__name__)

router = APIRouter(tags=["Streams"])

_ISO_FMT = "%Y-%m-%dT%H:%M:%S"


def _iso(value) -> Optional[str]:
    """Format a stream timestamp as the ISO string used everywhere else (None passes through)."""
    if value is None or isinstance(value, str):
        return value
    return value.strftime(_ISO_FMT)


def _sub_share(sub_messages, total_messages) -> Optional[float]:
    """sub_messages / total_messages; None when either is unknown or total is 0."""
    if sub_messages is None or total_messages is None or total_messages == 0:
        return None
    return sub_messages / total_messages


def _previous_rows(series_rows, start_str: Optional[str], stream_id: int, lookback: int) -> list:
    """Keep series rows strictly before this stream in (start, id) order; last `lookback` of them.

    Rows come from select_creator_report_series_db ascending by start:
    (stream_id, start_str, duration_seconds, total_messages, messages_per_minute,
     unique_chatters, new_chatters, returning_chatters, sub_messages, peak_messages).
    """
    if start_str is None:
        return []
    previous = [
        row for row in series_rows if row[1] is not None and (row[1], row[0]) < (start_str, stream_id)
    ]
    return previous[-lookback:]


def _top_moments(moment_rows) -> List[ReportMoment]:
    """Top 3 persisted moments by ratio DESC (None ratios last), excluding rejected ones."""
    accepted = [row for row in moment_rows if row[10] != "rejected"]
    ranked = sorted(accepted, key=lambda row: (row[4] is not None, row[4] or 0.0), reverse=True)
    return [
        ReportMoment(
            bucket_minute=row[0],
            offset_seconds=row[1],
            message_count=row[2],
            ratio=row[4],
            status=row[10],
        )
        for row in ranked[:3]
    ]


@router.get(
    "/stream/{stream_id}/report",
    response_model=StreamReport,
    summary="Get the report card for a stream",
    description=(
        "KPI scorecard for one stream, compared against the creator's previous rolled-up "
        "streams (delta vs baseline median + percentile rank)."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Stream not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_stream_report(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1}),
    lookback: int = Query(10, ge=2, le=30, description="Previous streams to use as baseline"),
) -> dict[str, Any]:
    """Build the report card for a single stream.

    404 only when the stream row itself does not exist. An un-rolled-up stream returns
    200 with all metric values None (nullable = unknown, never coalesced to 0). Baseline
    math uses only previous rolled-up streams; with fewer than 2 of them every
    delta_pct/percentile/baseline_median is None.
    """
    try:
        cache = get_cache()
        cache_key = cache._generate_key("stream_report", stream_id, lookback)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "stream_report")
            return cast(dict[str, Any], cached_result)

        record_cache_operation("miss", "stream_report")
        comprehensive = select_stream_comprehensive_db(stream_id)
        if comprehensive is None:
            raise HTTPException(status_code=404, detail="Stream not found")

        creator_id = comprehensive[8]
        start_str = _iso(comprehensive[1])

        metrics_row = select_stream_metrics_db(stream_id)
        sample_rows = select_stream_viewer_samples_db(stream_id)
        emote_rows = select_stream_emotes_db(stream_id, 1)
        phrase_rows = select_stream_phrases_db(stream_id, 1)
        moment_rows = select_stream_moments_db(stream_id)
        series_rows = select_creator_report_series_db(creator_id, lookback + 1)

        baseline_rows = _previous_rows(series_rows, start_str, stream_id, lookback)
        # Un-rolled-up previous streams (NULL total_messages / messages_per_minute)
        # never enter baseline math.
        survivors = [row for row in baseline_rows if row[3] is not None and row[4] is not None]
        baseline_count = len(survivors)

        if metrics_row is not None:
            total_messages = metrics_row[0]
            unique_chatters = metrics_row[1]
            duration_seconds = metrics_row[2]
            messages_per_minute = metrics_row[3]
            peak_messages = metrics_row[4]
            peak_bucket_minute = metrics_row[5]
            new_chatters = metrics_row[6]
            returning_chatters = metrics_row[7]
            sub_messages = metrics_row[8]
        else:
            total_messages = unique_chatters = duration_seconds = None
            messages_per_minute = peak_messages = peak_bucket_minute = None
            new_chatters = returning_chatters = sub_messages = None

        viewer_counts = [row[1] for row in sample_rows]
        avg_viewers = sum(viewer_counts) / len(viewer_counts) if viewer_counts else None
        peak_viewers = max(viewer_counts) if viewer_counts else None

        metrics = ReportMetrics(
            messages_per_minute=ReportMetric(
                **build_metric(messages_per_minute, [row[4] for row in survivors])
            ),
            total_messages=ReportMetric(**build_metric(total_messages, [row[3] for row in survivors])),
            unique_chatters=ReportMetric(**build_metric(unique_chatters, [row[5] for row in survivors])),
            new_chatters=ReportMetric(**build_metric(new_chatters, [row[6] for row in survivors])),
            returning_chatters=ReportMetric(
                **build_metric(returning_chatters, [row[7] for row in survivors])
            ),
            sub_share=ReportMetric(
                **build_metric(
                    _sub_share(sub_messages, total_messages),
                    [_sub_share(row[8], row[3]) for row in survivors],
                )
            ),
            peak_messages=ReportMetric(**build_metric(peak_messages, [row[9] for row in survivors])),
            # No baseline math for viewer metrics — historical viewer matching is out of scope.
            avg_viewers=ReportMetric(value=avg_viewers),
            peak_viewers=ReportMetric(value=peak_viewers),
        )

        result = StreamReport(
            stream_id=stream_id,
            creator_id=creator_id,
            creator_nick=comprehensive[5],
            title=comprehensive[0],
            start=start_str,
            end=_iso(comprehensive[2]),
            duration_seconds=duration_seconds,
            baseline_count=baseline_count,
            lookback=lookback,
            metrics=metrics,
            peak_bucket_minute=peak_bucket_minute,
            top_emote=TopEmote(
                name=emote_rows[0][0],
                source=emote_rows[0][1],
                provider_id=emote_rows[0][2],
                usage_count=emote_rows[0][3],
                chatter_count=emote_rows[0][4],
            )
            if emote_rows
            else None,
            top_phrase=TopPhrase(
                phrase=phrase_rows[0][0],
                usage_count=phrase_rows[0][1],
                chatter_count=phrase_rows[0][2],
            )
            if phrase_rows
            else None,
            top_moments=_top_moments(moment_rows),
        )
        payload = result.model_dump()
        cache.set(cache_key, payload, CacheTTL.STREAM_ANALYTICS)
        record_cache_operation("set", "stream_report")
        response.headers["X-Cache"] = "MISS"
        return payload
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching stream report: {exc}")
        record_cache_operation("error", "stream_report")
        raise HTTPException(status_code=500, detail="Internal server error")


_EXPORT_FIELDNAMES = ["id", "time", "chatter_id", "nick", "text", "is_subscriber", "badges"]

# The message replay SELECT (message_replay_gateway.select_stream_messages_db) without
# keyset cursor/LIMIT — the server-side cursor below paginates instead.
_EXPORT_SQL = """
    SELECT m.id, TO_CHAR(m.time, 'YYYY-MM-DD"T"HH24:MI:SS.US'), m.chatter_id, c.nick,
           mt.text, m.is_subscriber, m.badges
    FROM message m
    JOIN chatter c ON c.id = m.chatter_id
    JOIN message_text mt ON mt.id = m.message_text_id
    WHERE m.stream_id = %s
    ORDER BY m.time ASC, m.id ASC
"""


def _iter_export_rows(stream_id: int) -> Iterator[dict[str, Any]]:
    """Yield the full chat log as dict rows, holding one pooled connection for the whole stream.

    A psycopg2 NAMED cursor is server-side, so millions of rows never materialize in
    memory. @with_cursor gateways cannot be used here — they return the connection to
    the pool before iteration starts. The cursor is closed and the read transaction
    rolled back before putconn, also on client disconnect (GeneratorExit unwinds
    through finally/with).
    """
    pool = get_pool()
    with pool.get_connection() as connection:
        cursor = connection.cursor(name=f"chat_export_{stream_id}_{uuid4().hex}")
        cursor.itersize = 5000
        try:
            cursor.execute(_EXPORT_SQL, (stream_id,))
            for row in cursor:
                yield {
                    "id": row[0],
                    "time": row[1],
                    "chatter_id": row[2],
                    "nick": row[3],
                    "text": row[4],
                    "is_subscriber": row[5],
                    "badges": row[6],
                }
        finally:
            cursor.close()
            connection.rollback()


@router.get(
    "/stream/{stream_id}/export",
    summary="Export the full chat log for a stream",
    description="Streams every chat message of a stream as NDJSON or CSV. Requires authentication.",
    responses={
        401: {"description": "Authentication required"},
        404: {"model": ErrorResponse, "description": "Stream not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
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
    try:
        comprehensive = select_stream_comprehensive_db(stream_id)
    except Exception as exc:
        logger.error(f"Error preparing stream export: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")
    # 404 must be decided BEFORE streaming starts — the status is immutable afterwards.
    if comprehensive is None:
        raise HTTPException(status_code=404, detail="Stream not found")

    rows = _iter_export_rows(stream_id)
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
