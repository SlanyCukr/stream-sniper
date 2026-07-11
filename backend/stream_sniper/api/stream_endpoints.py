"""Read-only endpoints for Twitch stream listings and stream analytics."""

from datetime import date
from typing import Any, List, Optional, cast

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response

from ..database.chatter_table_gateway import select_all_chatters_on_stream_db
from ..database.stream_table_gateway import (
    select_all_stream_count_db,
    select_all_streams_db,
    select_chatter_messages_on_stream_db,
    select_chatters_in_stream_db,
    select_creators_that_wrote_in_stream_db,
    select_most_active_chatters_db,
    select_most_tagged_chatters_db,
    select_stream_comprehensive_db,
)
from ..logging_config import get_logger
from .cache import CacheTTL, get_cache
from .models import ErrorResponse, StreamDetails, StreamsResponse
from .monitoring import record_cache_operation
from .rate_limiter import limiter, rate_limits

logger = get_logger(__name__)

router = APIRouter(tags=["Streams"])


@router.get(
    "/streams",
    response_model=StreamsResponse,
    summary="Get streams with pagination",
    description="Retrieve streams for one creator, or all creators with `creator_id=-1`.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.BULK)
def get_streams(
    request: Request,
    response: Response,
    creator_id: int = Query(..., description="Creator ID (use -1 for all creators)", json_schema_extra={"example": 5}),
    offset: int = Query(0, description="Pagination offset", json_schema_extra={"example": 0}, ge=0),
    sort: str = Query(
        "start",
        description="Sort column",
        pattern="^(start|message_count|duration)$",
        json_schema_extra={"example": "start"},
    ),
    dir: str = Query(
        "desc",
        description="Sort direction",
        pattern="^(asc|desc)$",
        json_schema_extra={"example": "desc"},
    ),
    title: Optional[str] = Query(None, description="Filter by title substring (case-insensitive)", max_length=255),
    date_from: Optional[date] = Query(None, description="Only streams starting on/after this date"),
    date_to: Optional[date] = Query(None, description="Only streams starting before this date (exclusive, +1 day)"),
    min_messages: Optional[int] = Query(None, description="Minimum message count", ge=0),
) -> dict[str, Any]:
    """Get a paginated list of streams for a creator with optional sort/filter."""
    try:
        cache = get_cache()
        streams_cache_key = cache._generate_key(
            "streams", creator_id, offset, sort, dir, title, date_from, date_to, min_messages
        )
        cached_streams = cache.get(streams_cache_key)
        count_cache_key = cache._generate_key("stream_count", creator_id, title, date_from, date_to, min_messages)
        cached_count = cache.get(count_cache_key)
        streams_from_cache = cached_streams is not None
        count_from_cache = cached_count is not None

        if streams_from_cache:
            record_cache_operation("hit", "streams")
            streams = cached_streams
        else:
            record_cache_operation("miss", "streams")
            streams = select_all_streams_db(
                creator_id,
                offset,
                sort=sort,
                dir=dir,
                title=title,
                date_from=date_from,
                date_to=date_to,
                min_messages=min_messages,
            )
            cache.set(streams_cache_key, streams, CacheTTL.STREAM_DETAILS)
            record_cache_operation("set", "streams")

        if count_from_cache:
            record_cache_operation("hit", "stream_count")
            max_offset = cached_count
        else:
            record_cache_operation("miss", "stream_count")
            max_offset = select_all_stream_count_db(
                creator_id,
                title=title,
                date_from=date_from,
                date_to=date_to,
                min_messages=min_messages,
            )
            cache.set(count_cache_key, max_offset, CacheTTL.STREAM_COUNT)
            record_cache_operation("set", "stream_count")

        if streams_from_cache and count_from_cache:
            response.headers["X-Cache"] = "HIT"
        elif streams_from_cache or count_from_cache:
            response.headers["X-Cache"] = "PARTIAL"
        else:
            response.headers["X-Cache"] = "MISS"

        return {"streams": streams, "max_offset": max_offset}
    except Exception as exc:
        logger.error(f"Error fetching streams: {exc}")
        record_cache_operation("error", "streams")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/stream/{stream_id}/chatters",
    response_model=List[List[Any]],
    summary="Get all chatters in a stream",
    description="Retrieve all unique chatters who participated in one stream.",
    responses={
        404: {"model": ErrorResponse, "description": "Stream not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def get_stream_chatters(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1}),
) -> list[list[Any]]:
    """Get all chatters who participated in a stream."""
    try:
        cache = get_cache()
        cache_key = cache._generate_key("stream_chatters", stream_id)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "stream_chatters")
            return cast(list[list[Any]], cached_result)

        record_cache_operation("miss", "stream_chatters")
        result = select_all_chatters_on_stream_db(stream_id)
        if not result:
            raise HTTPException(status_code=404, detail="Stream not found or has no chatters")

        cache.set(cache_key, result, CacheTTL.STREAM_DETAILS)
        record_cache_operation("set", "stream_chatters")
        response.headers["X-Cache"] = "MISS"
        return cast(list[list[Any]], result)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching stream chatters: {exc}")
        record_cache_operation("error", "stream_chatters")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/stream/{stream_id}",
    response_model=StreamDetails,
    summary="Get comprehensive stream analytics",
    description="Return stream details, active and tagged chatters, creator activity, and participants.",
    responses={
        404: {"model": ErrorResponse, "description": "Stream not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_stream(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1}),
) -> dict[str, Any]:
    """Get comprehensive analytics for a stream."""
    try:
        cache = get_cache()
        analytics_cache_key = cache._generate_key("stream_analytics", stream_id)
        cached_analytics = cache.get(analytics_cache_key)
        if cached_analytics is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "stream_analytics")
            return cast(dict[str, Any], cached_analytics)

        record_cache_operation("miss", "stream_analytics")
        comprehensive_stream_info = select_stream_comprehensive_db(stream_id)
        if not comprehensive_stream_info:
            raise HTTPException(status_code=404, detail="Stream not found")

        analytics_data = {
            "csi": comprehensive_stream_info,
            "mac": select_most_active_chatters_db(stream_id),
            "mtc": select_most_tagged_chatters_db(stream_id),
            "octw": select_creators_that_wrote_in_stream_db(stream_id, comprehensive_stream_info[8]),
            "cis": select_chatters_in_stream_db(stream_id),
        }
        cache.set(analytics_cache_key, analytics_data, CacheTTL.STREAM_ANALYTICS)
        record_cache_operation("set", "stream_analytics")
        response.headers["X-Cache"] = "MISS"
        return analytics_data
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching stream analytics: {exc}")
        record_cache_operation("error", "stream_analytics")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/stream/{stream_id}/chatter/{chatter_id}/messages",
    response_model=List[str],
    summary="Get chatter messages in a stream",
    description="Retrieve all messages sent by a chatter during one stream.",
    responses={
        404: {"model": ErrorResponse, "description": "Stream or chatter not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def get_chatter_messages_on_stream(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1}),
    chatter_id: int = Path(..., description="Unique chatter ID", json_schema_extra={"example": 42}),
) -> list[str]:
    """Get messages from a specific chatter in a specific stream."""
    try:
        cache = get_cache()
        cache_key = cache._generate_key("chatter_stream_messages", stream_id, chatter_id)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "chatter_stream_messages")
            return cast(list[str], cached_result)

        record_cache_operation("miss", "chatter_stream_messages")
        result = select_chatter_messages_on_stream_db(stream_id, chatter_id)
        if not result:
            raise HTTPException(status_code=404, detail="No messages found for this chatter in this stream")

        messages = [message[0] for message in result]
        cache.set(cache_key, messages, CacheTTL.CHATTER_MESSAGES)
        record_cache_operation("set", "chatter_stream_messages")
        response.headers["X-Cache"] = "MISS"
        return cast(list[str], messages)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching chatter messages on stream: {exc}")
        record_cache_operation("error", "chatter_stream_messages")
        raise HTTPException(status_code=500, detail="Internal server error")
