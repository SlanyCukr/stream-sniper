"""Read-only endpoints for Twitch chat participants and their messages."""

from typing import Any, cast

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response
from pydantic import RootModel

from ....application.chatters.passport_models import ChatterPassport
from ....application.chatters.passport_query import get_chatter_passport as query_chatter_passport
from ....application.chatters.versus_models import ChatterHeadToHead
from ....application.chatters.versus_query import (
    ChatterVersusNotFoundError,
)
from ....application.chatters.versus_query import (
    get_chatter_head_to_head as query_chatter_head_to_head,
)
from ....database.gateways.chat.chatter_table_gateway import select_chatters_by_prefix_db
from ....database.gateways.chat.message_table_gateway import (
    select_chatter_identity_db,
    select_chatter_message_count_db,
    select_chatter_messages_db,
    select_chatter_stream_activity_db,
)
from ....logging_config import get_logger
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy, record_cache_failures
from ...caching.rollup_version import scene_rollup_version
from ...dependencies import get_cache
from ...observability.monitoring import record_cache_operation
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import ErrorResponse, RateLimitErrorResponse
from .chatter_models import (
    ChatterActivity,
    ChatterIdentity,
    ChatterMessage,
    ChatterMessagesResponse,
    ChatterSearchResult,
)

logger = get_logger(__name__)

router = APIRouter(tags=["Chatters"])


class _ChatterSearchCache(RootModel[list[ChatterSearchResult]]):
    pass


class _ChatterActivityCache(RootModel[list[ChatterActivity]]):
    pass


_CHATTER_ID_CACHE = ModelCachePolicy("chatter_id", CacheTTL.CHATTER_MESSAGES, ChatterIdentity)
_CHATTER_SEARCH_CACHE = ModelCachePolicy("chatter_search", CacheTTL.CHATTER_SEARCH, _ChatterSearchCache)
_CHATTER_ACTIVITY_CACHE = ModelCachePolicy("chatter_stream_activity", CacheTTL.STREAM_DETAILS, _ChatterActivityCache)
_CHATTER_PASSPORT_CACHE = ModelCachePolicy("chatter_passport", CacheTTL.STREAM_ANALYTICS, ChatterPassport)
_CHATTER_VERSUS_CACHE = ModelCachePolicy("chatter_head_to_head", CacheTTL.STREAM_ANALYTICS, ChatterHeadToHead)


@router.get(
    "/chatters/head-to-head",
    response_model=ChatterHeadToHead,
    summary="Compare two chatters head-to-head",
    description=(
        "Pairwise chatter comparison: lifetime totals, home channel, and archetype badges per side, "
        "plus the streams and channels both attended. Side `a` is always the lower chatter id."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "The two chatter ids are identical"},
        404: {"model": ErrorResponse, "description": "One or both chatters are unknown"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_chatter_head_to_head(
    request: Request,
    response: Response,
    chatter_a: int = Query(..., description="First chatter ID", ge=1),
    chatter_b: int = Query(..., description="Second chatter ID", ge=1),
) -> ChatterHeadToHead:
    """Pairwise chatter comparison built from the chatter rollups."""
    if chatter_a == chatter_b:
        raise HTTPException(status_code=400, detail="Pick two different chatters to compare.")
    with _CHATTER_VERSUS_CACHE.record_failures():
        cache = get_cache(request)
        # Normalized to (lo, hi) so the cached payload is order-independent:
        # side `a` is always the lower chatter id, whatever the param order.
        lo, hi = sorted((chatter_a, chatter_b))
        cache_key, cached_result = _CHATTER_VERSUS_CACHE.lookup(cache, response, lo, hi, scene_rollup_version())
        if cached_result is not None:
            return cached_result

        try:
            result = query_chatter_head_to_head(lo, hi)
        except ChatterVersusNotFoundError:
            raise HTTPException(status_code=404, detail="One of these chatters is not in the corpus.") from None

        _CHATTER_VERSUS_CACHE.store(cache, response, cache_key, result)
        return result


@router.get(
    "/chatters/{chatter_id}/messages",
    response_model=ChatterMessagesResponse,
    summary="Get messages by chatter",
    description=(
        "Retrieve a chatter's messages across all streams, newest first, with pagination. "
        "Each row contains stream context and the overall message count."
    ),
    responses={429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.GENERAL)
def get_chatter_messages(
    request: Request,
    response: Response,
    chatter_id: int = Path(..., description="Unique chatter ID", json_schema_extra={"example": 42}),
    offset: int = Query(0, ge=0, description="Row offset for pagination", json_schema_extra={"example": 0}),
    limit: int = Query(50, ge=1, le=200, description="Maximum messages per page"),
) -> ChatterMessagesResponse:
    """Get a paginated cross-stream message log for one chatter."""
    with record_cache_failures("chatter_messages"):
        cache = get_cache(request)
        messages_cache_key = cache.generate_key("chatter_messages", chatter_id, limit, offset)
        cached_messages = cache.get(messages_cache_key)
        count_cache_key = cache.generate_key("chatter_message_count", chatter_id)
        cached_count = cache.get(count_cache_key)

        messages_from_cache = cached_messages is not None
        count_from_cache = cached_count is not None

        if messages_from_cache:
            record_cache_operation("hit", "chatter_messages")
            messages = [ChatterMessage.model_validate(row) for row in cast(list[dict[str, Any]], cached_messages)]
        else:
            record_cache_operation("miss", "chatter_messages")
            messages = [
                ChatterMessage(
                    stream_id=row.stream_id,
                    stream_title=row.stream_title,
                    creator_display_name=row.creator_display_name,
                    text=row.text,
                    timestamp=str(row.sent_at),
                )
                for row in select_chatter_messages_db(chatter_id, limit, offset)
            ]
            cache.set(messages_cache_key, [message.model_dump() for message in messages], CacheTTL.CHATTER_MESSAGES)
            record_cache_operation("set", "chatter_messages")

        if cached_count is not None:
            record_cache_operation("hit", "chatter_message_count")
            total = int(cached_count)
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

        return ChatterMessagesResponse(messages=messages, total=total, offset=offset, limit=limit)


@router.get(
    "/chatters/by-nick/{nick}",
    response_model=ChatterIdentity,
    summary="Get chatter ID by nickname",
    description=(
        "Look up a chatter's unique ID using their nickname. "
        "Returns a named identity with a nullable bot-classification flag."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Chatter not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.SEARCH)
def get_chatter_identity(
    request: Request,
    response: Response,
    nick: str = Path(..., description="Chatter nickname", json_schema_extra={"example": "viewer123"}),
) -> ChatterIdentity:
    """Get a chatter ID (and bot flag) by nickname."""
    with _CHATTER_ID_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _CHATTER_ID_CACHE.lookup(cache, response, nick)
        if cached_result is not None:
            return cached_result

        result = select_chatter_identity_db(nick)
        if not result:
            raise HTTPException(status_code=404, detail="Chatter not found")

        identity = ChatterIdentity(chatter_id=result.id, is_bot=result.is_bot)
        _CHATTER_ID_CACHE.store(cache, response, cache_key, identity)
        return identity


@router.get(
    "/chatters/search",
    response_model=list[ChatterSearchResult],
    summary="Search chatters by nickname prefix",
    description=(
        "Case-insensitive prefix search over chatter nicknames for autocomplete. "
        "Results include named identity fields and a nullable bot flag; bots are badged, not hidden."
    ),
    responses={429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.SEARCH)
def search_chatters(
    request: Request,
    response: Response,
    q: str = Query(..., description="Nickname prefix to search for", json_schema_extra={"example": "nin"}),
    limit: int = Query(10, ge=1, le=25, description="Maximum number of suggestions"),
) -> list[ChatterSearchResult]:
    """Prefix-search chatter nicknames for autocomplete suggestions."""
    prefix = q.strip()
    if len(prefix) < 2:
        return []

    with _CHATTER_SEARCH_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _CHATTER_SEARCH_CACHE.lookup(cache, response, prefix.lower(), limit)
        if cached_result is not None:
            return cached_result.root

        result = [
            ChatterSearchResult(chatter_id=row.chatter_id, nick=row.nick, is_bot=row.is_bot)
            for row in select_chatters_by_prefix_db(prefix, limit)
        ]
        _CHATTER_SEARCH_CACHE.store(cache, response, cache_key, _ChatterSearchCache(result))
        return result


@router.get(
    "/chatters/{chatter_id}/stream-activity",
    response_model=list[ChatterActivity],
    summary="Get a chatter's stream activity",
    description="Return the streams in which a chatter participated and their message counts.",
    responses={429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.GENERAL)
def get_chatter_stream_activity(
    request: Request,
    response: Response,
    chatter_id: int = Path(..., description="Unique chatter ID", json_schema_extra={"example": 42}),
) -> list[ChatterActivity]:
    """Get a chatter's cross-stream activity footprint."""
    with _CHATTER_ACTIVITY_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _CHATTER_ACTIVITY_CACHE.lookup(cache, response, chatter_id)
        if cached_result is not None:
            return cached_result.root

        result = [
            ChatterActivity(
                stream_id=row.stream_id,
                stream_title=row.stream_title,
                start=str(row.stream_start),
                creator_id=row.creator_id,
                creator_display_name=row.creator_display_name,
                message_count=row.message_count,
                is_bot=row.is_bot,
            )
            for row in select_chatter_stream_activity_db(chatter_id)
        ]
        _CHATTER_ACTIVITY_CACHE.store(cache, response, cache_key, _ChatterActivityCache(result))
        return result


@router.get(
    "/chatters/{chatter_id}/passport",
    response_model=ChatterPassport,
    summary="Get a chatter's identity passport",
    description=(
        "A public per-chatter profile: totals across the whole corpus, their debut message, "
        "home channel, per-creator loyalty (ranked by messages), and their most-active stream."
    ),
    responses={
        404: {"model": ErrorResponse, "description": "Chatter not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_chatter_passport(
    request: Request,
    response: Response,
    chatter_id: int = Path(..., description="Unique chatter ID", json_schema_extra={"example": 42}),
) -> ChatterPassport:
    """Assemble a chatter's cross-corpus identity passport."""
    with _CHATTER_PASSPORT_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _CHATTER_PASSPORT_CACHE.lookup(cache, response, chatter_id, scene_rollup_version())
        if cached_result is not None:
            return cached_result

        result = query_chatter_passport(chatter_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Chatter not found")

        _CHATTER_PASSPORT_CACHE.store(cache, response, cache_key, result)
        return result
