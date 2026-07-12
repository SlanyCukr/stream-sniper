"""Read-only endpoint for chronological stream chat message replay."""

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response

from ..database.message_replay_gateway import select_stream_messages_db
from ..logging_config import get_logger
from .cache import CacheTTL, get_cache
from .message_models import MessagePage
from .models import ErrorResponse
from .monitoring import record_cache_operation
from .rate_limiter import limiter, rate_limits

logger = get_logger(__name__)

router = APIRouter(tags=["Streams"])


@router.get(
    "/stream/{stream_id}/messages",
    response_model=MessagePage,
    summary="Replay stream messages chronologically",
    description="Keyset-paginated replay of all messages in a stream, oldest to newest.",
    responses={
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def get_stream_messages(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1}),
    after_ts: Optional[str] = Query(None, description="Keyset cursor: timestamp of the last seen message"),
    after_id: Optional[int] = Query(None, description="Keyset cursor: ID of the last seen message"),
    limit: int = Query(100, description="Page size", ge=1, le=200),
    chatter_id: Optional[int] = Query(None, description="Filter to one chatter"),
    q: Optional[str] = Query(None, description="Case-insensitive substring filter on message text", max_length=255),
    sub_only: bool = Query(False, description="Restrict to messages sent by subscribers"),
) -> dict[str, Any]:
    """Get a chronological page of messages for a stream."""
    try:
        cache = get_cache()
        cache_key = cache._generate_key(
            "stream_messages",
            stream_id,
            after_ts or "",
            after_id or 0,
            limit,
            chatter_id or 0,
            (q or "").lower(),
            sub_only,
        )
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "stream_messages")
            return cached_result

        record_cache_operation("miss", "stream_messages")
        rows = select_stream_messages_db(
            stream_id,
            limit,
            after_ts=after_ts,
            after_id=after_id,
            chatter_id=chatter_id,
            q=q,
            sub_only=sub_only,
        )

        messages = [
            {
                "id": row[0],
                "time": row[1],
                "chatter_id": row[2],
                "nick": row[3],
                "text": row[4],
                "is_subscriber": row[5],
                "badges": row[6],
            }
            for row in rows
        ]
        if len(messages) == limit:
            last = messages[-1]
            next_cursor = {"after_ts": last["time"], "after_id": last["id"]}
        else:
            next_cursor = None

        result = {
            "messages": messages,
            "next_cursor": next_cursor,
            "has_more": next_cursor is not None,
        }
        cache.set(cache_key, result, CacheTTL.STREAM_DETAILS)
        record_cache_operation("set", "stream_messages")
        response.headers["X-Cache"] = "MISS"
        return result
    except Exception as exc:
        logger.error(f"Error fetching stream messages: {exc}")
        record_cache_operation("error", "stream_messages")
        raise HTTPException(status_code=500, detail="Internal server error")
