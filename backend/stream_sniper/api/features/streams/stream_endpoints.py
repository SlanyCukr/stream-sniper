"""Read-only endpoints for Twitch stream listings and stream analytics."""

from datetime import date
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response
from pydantic import RootModel

from ....application.streams.catalog_models import (
    StreamDetails,
    StreamListItem,
    StreamParticipant,
    StreamsResponse,
)
from ....application.streams.catalog_query import (
    count_streams as query_count_streams,
)
from ....application.streams.catalog_query import (
    list_streams as query_list_streams,
)
from ....application.streams.catalog_query import (
    stream_details as query_stream_details,
)
from ....database.gateways.chat.chatter_table_gateway import select_all_chatters_on_stream_db
from ....database.gateways.streams.stream_table_gateway import (
    select_chatter_messages_on_stream_db,
)
from ....logging_config import get_logger
from ...caching.cache import CacheTTL, InProcessCache
from ...caching.model_cache import ModelCachePolicy, record_cache_failures
from ...caching.rollup_version import stream_rollup_version
from ...dependencies import get_cache
from ...observability.monitoring import record_cache_operation
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import ErrorResponse, RateLimitErrorResponse

logger = get_logger(__name__)

router = APIRouter(tags=["Streams"])


class _StreamParticipantCache(RootModel[list[StreamParticipant]]):
    pass


_STREAM_CHATTERS_CACHE = ModelCachePolicy("stream_chatters", CacheTTL.STREAM_DETAILS, _StreamParticipantCache)
_STREAM_DETAILS_CACHE = ModelCachePolicy("stream_analytics", CacheTTL.STREAM_ANALYTICS, StreamDetails)


def _load_stream_page(
    cache: InProcessCache,
    cache_key: str,
    *,
    creator_id: int,
    offset: int,
    limit: int,
    sort: str,
    direction: str,
    title: str | None,
    date_from: date | None,
    date_to: date | None,
    min_messages: int | None,
) -> tuple[list[StreamListItem], bool]:
    cached = cache.get(cache_key)
    if cached is not None:
        record_cache_operation("hit", "streams")
        rows = cast(list[dict[str, Any]], cached)
        return [StreamListItem.model_validate(row) for row in rows], True

    record_cache_operation("miss", "streams")
    streams = query_list_streams(
        creator_id,
        offset,
        limit,
        sort=sort,
        direction=direction,
        title=title,
        date_from=date_from,
        date_to=date_to,
        min_messages=min_messages,
    )
    cache.set(cache_key, [row.model_dump() for row in streams], CacheTTL.STREAM_DETAILS)
    record_cache_operation("set", "streams")
    return streams, False


def _load_stream_count(
    cache: InProcessCache,
    cache_key: str,
    *,
    creator_id: int,
    title: str | None,
    date_from: date | None,
    date_to: date | None,
    min_messages: int | None,
) -> tuple[int, bool]:
    cached = cache.get(cache_key)
    if cached is not None:
        record_cache_operation("hit", "stream_count")
        return int(cached), True

    record_cache_operation("miss", "stream_count")
    total = query_count_streams(
        creator_id,
        title=title,
        date_from=date_from,
        date_to=date_to,
        min_messages=min_messages,
    )
    cache.set(cache_key, total, CacheTTL.STREAM_COUNT)
    record_cache_operation("set", "stream_count")
    return total, False


@router.get(
    "/streams",
    response_model=StreamsResponse,
    summary="Get streams with pagination",
    description="Retrieve streams for one creator, or all creators with `creator_id=-1`.",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid parameters"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.BULK)
def get_streams(
    request: Request,
    response: Response,
    creator_id: int = Query(..., description="Creator ID (use -1 for all creators)", json_schema_extra={"example": 5}),
    offset: int = Query(0, description="Pagination offset", json_schema_extra={"example": 0}, ge=0),
    limit: int = Query(20, description="Maximum streams per page", ge=1, le=100),
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
    title: str | None = Query(None, description="Filter by title substring (case-insensitive)", max_length=255),
    date_from: date | None = Query(None, description="Only streams starting on/after this date"),
    date_to: date | None = Query(None, description="Only streams starting before this date (exclusive, +1 day)"),
    min_messages: int | None = Query(None, description="Minimum message count", ge=0),
) -> StreamsResponse:
    """Get a paginated list of streams for a creator with optional sort/filter."""
    with record_cache_failures("streams"):
        cache = get_cache(request)
        streams_cache_key = cache.generate_key(
            "streams", creator_id, offset, limit, sort, dir, title, date_from, date_to, min_messages
        )
        count_cache_key = cache.generate_key("stream_count", creator_id, title, date_from, date_to, min_messages)
        streams, streams_from_cache = _load_stream_page(
            cache,
            streams_cache_key,
            creator_id=creator_id,
            offset=offset,
            limit=limit,
            sort=sort,
            direction=dir,
            title=title,
            date_from=date_from,
            date_to=date_to,
            min_messages=min_messages,
        )
        total, count_from_cache = _load_stream_count(
            cache,
            count_cache_key,
            creator_id=creator_id,
            title=title,
            date_from=date_from,
            date_to=date_to,
            min_messages=min_messages,
        )

        if streams_from_cache and count_from_cache:
            response.headers["X-Cache"] = "HIT"
        elif streams_from_cache or count_from_cache:
            response.headers["X-Cache"] = "PARTIAL"
        else:
            response.headers["X-Cache"] = "MISS"

        return StreamsResponse(streams=streams, total=total, offset=offset, limit=limit)


@router.get(
    "/streams/{stream_id}/chatters",
    response_model=list[StreamParticipant],
    summary="Get all chatters in a stream",
    description="Retrieve all unique chatters who participated in one stream.",
    responses={
        404: {"model": ErrorResponse, "description": "Stream not found or has no chatters"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def get_stream_chatters(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1}),
) -> list[StreamParticipant]:
    """Get all chatters who participated in a stream."""
    with _STREAM_CHATTERS_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _STREAM_CHATTERS_CACHE.lookup(
            cache, response, stream_id, stream_rollup_version(stream_id)
        )
        if cached_result is not None:
            return cached_result.root

        rows = select_all_chatters_on_stream_db(stream_id)
        if not rows:
            raise HTTPException(status_code=404, detail="Stream not found or has no chatters")

        result = [StreamParticipant(chatter_id=row.chatter_id, nick=row.nick) for row in rows]
        _STREAM_CHATTERS_CACHE.store(cache, response, cache_key, _StreamParticipantCache(result))
        return result


@router.get(
    "/streams/{stream_id}",
    response_model=StreamDetails,
    summary="Get comprehensive stream analytics",
    description="Return stream details, active and tagged chatters, creator activity, and participants.",
    responses={
        404: {"model": ErrorResponse, "description": "Stream not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_stream(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1}),
) -> StreamDetails:
    """Get comprehensive analytics for a stream."""
    with _STREAM_DETAILS_CACHE.record_failures():
        cache = get_cache(request)
        analytics_cache_key, cached_analytics = _STREAM_DETAILS_CACHE.lookup(
            cache, response, stream_id, stream_rollup_version(stream_id)
        )
        if cached_analytics is not None:
            return cached_analytics

        analytics_data = query_stream_details(stream_id)
        if analytics_data is None:
            raise HTTPException(status_code=404, detail="Stream not found")
        _STREAM_DETAILS_CACHE.store(cache, response, analytics_cache_key, analytics_data)
        return analytics_data


@router.get(
    "/streams/{stream_id}/chatters/{chatter_id}/messages",
    response_model=list[str],
    summary="Get chatter messages in a stream",
    description="Retrieve all messages sent by a chatter during one stream.",
    responses={
        404: {"model": ErrorResponse, "description": "Stream, chatter, or matching messages not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
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
    with record_cache_failures("chatter_stream_messages"):
        cache = get_cache(request)
        cache_key = cache.generate_key("chatter_stream_messages", stream_id, chatter_id)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "chatter_stream_messages")
            return cast(list[str], cached_result)

        record_cache_operation("miss", "chatter_stream_messages")
        result = select_chatter_messages_on_stream_db(stream_id, chatter_id)
        if not result:
            raise HTTPException(status_code=404, detail="No messages found for this chatter in this stream")

        messages = [message.text for message in result]
        cache.set(cache_key, messages, CacheTTL.CHATTER_MESSAGES)
        record_cache_operation("set", "chatter_stream_messages")
        response.headers["X-Cache"] = "MISS"
        return cast(list[str], messages)
