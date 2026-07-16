"""Read-only endpoints for Twitch creators and their audience summaries."""

from fastapi import APIRouter, Path, Query, Request, Response
from pydantic import RootModel

from ....database.gateways.identity.creator_table_gateway import select_creator_top_chatters_db, select_creators_db
from ....logging_config import get_logger
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy
from ...dependencies import get_cache
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import RateLimitErrorResponse
from .creator_models import CreatorListItem, CreatorTopChatter

logger = get_logger(__name__)

router = APIRouter(tags=["Creators"])


class _CreatorListCache(RootModel[list[CreatorListItem]]):
    pass


class _TopChatterListCache(RootModel[list[CreatorTopChatter]]):
    pass


_CREATORS_CACHE = ModelCachePolicy("creators", CacheTTL.CREATORS, _CreatorListCache)
_TOP_CHATTERS_CACHE = ModelCachePolicy("creator_top_chatters", CacheTTL.STREAM_DETAILS, _TopChatterListCache)


@router.get(
    "/creators",
    response_model=list[CreatorListItem],
    summary="Get all creators",
    description="Retrieve the ID and display name of every creator in the database.",
    responses={429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.GENERAL)
def get_creators(request: Request, response: Response) -> list[CreatorListItem]:
    """Get all creators in the database."""
    with _CREATORS_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _CREATORS_CACHE.lookup(cache, response)
        if cached_result is not None:
            return cached_result.root

        result = [
            CreatorListItem(creator_id=row.creator_id, display_name=row.display_name) for row in select_creators_db()
        ]
        _CREATORS_CACHE.store(cache, response, cache_key, _CreatorListCache(result))
        return result


@router.get(
    "/creators/{creator_id}/top-chatters",
    response_model=list[CreatorTopChatter],
    summary="Get a creator's most active chatters",
    description="Return named chatter activity summaries across all streams for one creator.",
    responses={429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.GENERAL)
def get_creator_top_chatters(
    request: Request,
    response: Response,
    creator_id: int = Path(..., description="Unique creator ID", json_schema_extra={"example": 5}),
    limit: int = Query(
        25, ge=1, le=200, description="Maximum number of chatters to return", json_schema_extra={"example": 25}
    ),
) -> list[CreatorTopChatter]:
    """Get the most active chatters across a creator's streams."""
    with _TOP_CHATTERS_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _TOP_CHATTERS_CACHE.lookup(cache, response, creator_id, limit)
        if cached_result is not None:
            return cached_result.root

        result = [
            CreatorTopChatter(chatter_id=row.chatter_id, nick=row.nick, message_count=row.message_count)
            for row in select_creator_top_chatters_db(creator_id, limit)
        ]
        _TOP_CHATTERS_CACHE.store(cache, response, cache_key, _TopChatterListCache(result))
        return result
