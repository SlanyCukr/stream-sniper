"""Read-only endpoint for chronological stream chat message replay."""

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response

from ....application.streams.message_models import MessagePage
from ....application.streams.message_page_query import get_message_page
from ....logging_config import get_logger
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy
from ...dependencies import get_cache
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import ErrorOrValidationResponse, RateLimitErrorResponse

logger = get_logger(__name__)

router = APIRouter(tags=["Streams"])

_MESSAGE_CACHE = ModelCachePolicy("stream_messages", CacheTTL.STREAM_DETAILS, MessagePage)


@router.get(
    "/streams/{stream_id}/messages",
    response_model=MessagePage,
    summary="Replay stream messages chronologically",
    description="Keyset-paginated replay of all messages in a stream, oldest to newest.",
    responses={
        422: {"model": ErrorOrValidationResponse, "description": "Invalid replay cursor or query parameter"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def get_stream_messages(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1}),
    after_ts: str | None = Query(None, description="Keyset cursor: timestamp of the last seen message"),
    after_id: int | None = Query(None, description="Keyset cursor: ID of the last seen message"),
    limit: int = Query(100, description="Page size", ge=1, le=200),
    chatter_id: int | None = Query(None, description="Filter to one chatter"),
    q: str | None = Query(None, description="Case-insensitive substring filter on message text", max_length=255),
    sub_only: bool = Query(False, description="Restrict to messages sent by subscribers"),
) -> MessagePage:
    """Get a chronological page of messages for a stream."""
    if (after_ts is None) != (after_id is None):
        raise HTTPException(status_code=422, detail="after_ts and after_id must be supplied together")
    with _MESSAGE_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _MESSAGE_CACHE.lookup(
            cache,
            response,
            stream_id,
            after_ts or "",
            after_id or 0,
            limit,
            chatter_id or 0,
            (q or "").lower(),
            sub_only,
        )
        if cached_result is not None:
            return cached_result

        result = get_message_page(
            stream_id,
            limit,
            after_ts=after_ts,
            after_id=after_id,
            chatter_id=chatter_id,
            q=q,
            sub_only=sub_only,
        )
        _MESSAGE_CACHE.store(cache, response, cache_key, result)
        return result
