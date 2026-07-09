"""Read-only endpoints for Twitch chat participants and their messages."""

from typing import Any, cast

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response

from ..database.chatter_table_gateway import select_chatters_by_prefix_db
from ..database.message_table_gateway import (
    select_chatter_id_db,
    select_chatter_message_count_db,
    select_chatter_messages_db,
    select_chatter_stream_activity_db,
)
from ..logging_config import get_logger
from .cache import CacheTTL, get_cache
from .models import ChatterMessagesResponse, ErrorResponse
from .monitoring import record_cache_operation
from .rate_limiter import limiter, rate_limits

logger = get_logger(__name__)

router = APIRouter(tags=["Chatters"])


@router.get(
    "/chatter/{chatter_id}/messages",
    response_model=ChatterMessagesResponse,
    summary="Get messages by chatter",
    description=(
        "Retrieve a chatter's messages across all streams, newest first, with pagination. "
        "Each row contains stream context and the overall message count."
    ),
    responses={429: {"model": ErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.GENERAL)
def get_chatter_messages(
    request: Request,
    response: Response,
    chatter_id: int = Path(..., description="Unique chatter ID", json_schema_extra={"example": 42}),
    offset: int = Query(0, ge=0, description="Row offset for pagination", json_schema_extra={"example": 0}),
    limit: int = Query(50, ge=1, le=200, description="Maximum messages per page"),
) -> dict[str, Any]:
    """Get a paginated cross-stream message log for one chatter."""
    try:
        cache = get_cache()
        messages_cache_key = cache._generate_key("chatter_messages", chatter_id, limit, offset)
        cached_messages = cache.get(messages_cache_key)
        count_cache_key = cache._generate_key("chatter_message_count", chatter_id)
        cached_count = cache.get(count_cache_key)

        messages_from_cache = cached_messages is not None
        count_from_cache = cached_count is not None

        if messages_from_cache:
            record_cache_operation("hit", "chatter_messages")
            messages = cached_messages
        else:
            record_cache_operation("miss", "chatter_messages")
            messages = select_chatter_messages_db(chatter_id, limit, offset)
            cache.set(messages_cache_key, messages, CacheTTL.CHATTER_MESSAGES)
            record_cache_operation("set", "chatter_messages")

        if count_from_cache:
            record_cache_operation("hit", "chatter_message_count")
            total = cached_count
        else:
            record_cache_operation("miss", "chatter_message_count")
            total = select_chatter_message_count_db(chatter_id)
            cache.set(count_cache_key, total, CacheTTL.CHATTER_MESSAGES)
            record_cache_operation("set", "chatter_message_count")

        if messages_from_cache and count_from_cache:
            response.headers["X-Cache"] = "HIT"
        elif messages_from_cache or count_from_cache:
            response.headers["X-Cache"] = "PARTIAL"
        else:
            response.headers["X-Cache"] = "MISS"

        return {"messages": messages, "total": total}
    except Exception as exc:
        logger.error(f"Error fetching chatter messages: {exc}")
        record_cache_operation("error", "chatter_messages")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/chatter/{nick}/chatter_id",
    response_model=list[int],
    summary="Get chatter ID by nickname",
    description="Look up a chatter's unique ID using their nickname.",
    responses={
        404: {"model": ErrorResponse, "description": "Chatter not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.SEARCH)
def get_chatter_id(
    request: Request,
    response: Response,
    nick: str = Path(..., description="Chatter nickname", json_schema_extra={"example": "viewer123"}),
) -> list[int]:
    """Get a chatter ID by nickname."""
    try:
        cache = get_cache()
        cache_key = cache._generate_key("chatter_id", nick)
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "chatter_id")
            return cast(list[int], cached_result)

        record_cache_operation("miss", "chatter_id")
        result = select_chatter_id_db(nick)
        if not result:
            raise HTTPException(status_code=404, detail="Chatter not found")

        cache.set(cache_key, result, CacheTTL.CHATTER_MESSAGES)
        record_cache_operation("set", "chatter_id")
        response.headers["X-Cache"] = "MISS"
        return cast(list[int], result)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching chatter ID: {exc}")
        record_cache_operation("error", "chatter_id")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/chatters/search",
    response_model=list[list[Any]],
    summary="Search chatters by nickname prefix",
    description="Case-insensitive prefix search over chatter nicknames for autocomplete.",
    responses={429: {"model": ErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.SEARCH)
def search_chatters(
    request: Request,
    response: Response,
    q: str = Query(..., description="Nickname prefix to search for", json_schema_extra={"example": "nin"}),
    limit: int = Query(10, ge=1, le=25, description="Maximum number of suggestions"),
) -> list[list[Any]]:
    """Prefix-search chatter nicknames for autocomplete suggestions."""
    prefix = q.strip()
    if len(prefix) < 2:
        return []

    try:
        cache = get_cache()
        cache_key = cache._generate_key("chatter_search", prefix.lower(), limit)
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "chatter_search")
            return cast(list[list[Any]], cached_result)

        record_cache_operation("miss", "chatter_search")
        result = select_chatters_by_prefix_db(prefix, limit)
        cache.set(cache_key, result, CacheTTL.CHATTER_SEARCH)
        record_cache_operation("set", "chatter_search")
        response.headers["X-Cache"] = "MISS"
        return cast(list[list[Any]], result)
    except Exception as exc:
        logger.error(f"Error searching chatters: {exc}")
        record_cache_operation("error", "chatter_search")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/chatter/{chatter_id}/stream-activity",
    response_model=list[list[Any]],
    summary="Get a chatter's stream activity",
    description="Return the streams in which a chatter participated and their message counts.",
    responses={429: {"model": ErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.GENERAL)
def get_chatter_stream_activity(
    request: Request,
    response: Response,
    chatter_id: int = Path(..., description="Unique chatter ID", json_schema_extra={"example": 42}),
) -> list[list[Any]]:
    """Get a chatter's cross-stream activity footprint."""
    try:
        cache = get_cache()
        cache_key = cache._generate_key("chatter_stream_activity", chatter_id)
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "chatter_stream_activity")
            return cast(list[list[Any]], cached_result)

        record_cache_operation("miss", "chatter_stream_activity")
        result = select_chatter_stream_activity_db(chatter_id)
        cache.set(cache_key, result, CacheTTL.STREAM_DETAILS)
        record_cache_operation("set", "chatter_stream_activity")
        response.headers["X-Cache"] = "MISS"
        return cast(list[list[Any]], result)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching chatter stream activity: {exc}")
        record_cache_operation("error", "chatter_stream_activity")
        raise HTTPException(status_code=500, detail="Internal server error")
