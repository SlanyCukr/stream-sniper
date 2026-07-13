"""Compare two to four streams using existing bounded analytics rollups."""

from collections import defaultdict
from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException, Query, Request, Response

from ..database.stream_compare_table_gateway import (
    select_stream_compare_buckets_db,
    select_stream_compare_headers_db,
    select_stream_pair_retention_db,
)
from ..database.stream_viewer_sample_table_gateway import select_stream_viewer_samples_db
from ..logging_config import get_logger
from .cache import CacheTTL, get_cache
from .compare_models import CompareCurvePoint, ComparedStream, PairRetention, StreamComparison
from .models import ErrorResponse
from .rate_limiter import limiter, rate_limits

logger = get_logger(__name__)
router = APIRouter(tags=["Streams"])
_FMT = "%Y-%m-%dT%H:%M:%S"


def _share(part, total):
    return None if part is None or total in (None, 0) else round(part / total, 4)


def _normalise_curve(rows, start, duration):
    """Collapse an arbitrary stream timeline into at most 101 percentage slots."""
    if not rows:
        return []
    start_dt = datetime.strptime(start, _FMT) if start else None
    result = {}
    for index, row in enumerate(rows):
        if start_dt is not None and duration and duration > 0:
            elapsed = (datetime.strptime(row[1], _FMT) - start_dt).total_seconds()
            percent = min(100, max(0, round(elapsed * 100 / duration)))
        else:
            percent = round(index * 100 / max(1, len(rows) - 1))
        existing = result.setdefault(percent, [0, 0])
        existing[0] += row[2]
        existing[1] = max(existing[1], row[3])
    return [
        CompareCurvePoint(percent=percent, message_count=values[0], unique_chatters=values[1])
        for percent, values in sorted(result.items())
    ]


@router.get(
    "/streams/compare",
    response_model=StreamComparison,
    summary="Compare two to four streams",
    responses={
        404: {"model": ErrorResponse, "description": "One or more streams not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.HEAVY)
def compare_streams(
    request: Request,
    response: Response,
    stream_ids: List[int] = Query(..., min_length=2, max_length=4),
) -> StreamComparison:
    if len(set(stream_ids)) != len(stream_ids):
        raise HTTPException(status_code=422, detail="stream_ids must be unique")
    try:
        cache = get_cache()
        key = cache._generate_key("stream_compare", *stream_ids)
        cached = cache.get(key)
        if cached is not None:
            response.headers["X-Cache"] = "HIT"
            return StreamComparison(**cached)

        headers = select_stream_compare_headers_db(stream_ids)
        if len(headers) != len(stream_ids):
            raise HTTPException(status_code=404, detail="One or more streams not found")
        header_by_id = {row[0]: row for row in headers}
        bucket_map = defaultdict(list)
        for row in select_stream_compare_buckets_db(stream_ids):
            bucket_map[row[0]].append(row)

        streams = []
        for stream_id in stream_ids:
            row = header_by_id[stream_id]
            samples = select_stream_viewer_samples_db(stream_id)
            peak_viewers = max((sample[1] for sample in samples), default=None)
            streams.append(
                ComparedStream(
                    stream_id=row[0], creator_id=row[1], creator_nick=row[2],
                    creator_display_name=row[3], title=row[4], start=row[5],
                    duration_seconds=row[6], total_messages=row[7], messages_per_minute=row[8],
                    unique_chatters=row[9], new_chatters=row[10], returning_chatters=row[11],
                    sub_share=_share(row[12], row[7]), emote_share=_share(row[13], row[7]),
                    peak_messages=row[14], peak_bucket_minute=row[15], peak_viewers=peak_viewers,
                    curve=_normalise_curve(bucket_map[stream_id], row[5], row[6]),
                )
            )

        retention = [
            PairRetention(
                from_stream_id=row[0], to_stream_id=row[1], from_audience=row[2],
                to_audience=row[3], retained=row[4],
                retention_rate=round(row[4] / row[2], 4) if row[2] else None,
            )
            for row in select_stream_pair_retention_db(stream_ids)
        ]
        result = StreamComparison(streams=streams, retention=retention)
        cache.set(key, result.model_dump(), CacheTTL.STREAM_ANALYTICS)
        response.headers["X-Cache"] = "MISS"
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error comparing streams: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")
