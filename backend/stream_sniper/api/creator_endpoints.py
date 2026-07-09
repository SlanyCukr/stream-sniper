"""Read-only endpoints for Twitch creators and their audience summaries."""

from typing import Any, cast

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response

from ..database.creator_table_gateway import select_creator_top_chatters_db, select_creators_db
from ..logging_config import get_logger
from .cache import CacheTTL, get_cache
from .models import ErrorResponse
from .monitoring import record_cache_operation
from .rate_limiter import limiter, rate_limits

logger = get_logger(__name__)

router = APIRouter(tags=["Creators"])


@router.get(
    "/creators",
    response_model=list[list[Any]],
    summary="Get all creators",
    description="Retrieve the ID and display name of every creator in the database.",
    responses={429: {"model": ErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.GENERAL)
def get_creators(request: Request, response: Response) -> list[list[Any]]:
    """Get all creators in the database."""
    try:
        cache = get_cache()
        cache_key = cache._generate_key("creators")
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "creators")
            return cast(list[list[Any]], cached_result)

        record_cache_operation("miss", "creators")
        result = select_creators_db()
        cache.set(cache_key, result, CacheTTL.CREATORS)
        record_cache_operation("set", "creators")
        response.headers["X-Cache"] = "MISS"
        return cast(list[list[Any]], result)
    except Exception as exc:
        logger.error(f"Error fetching creators: {exc}")
        record_cache_operation("error", "creators")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/creator/{creator_id}/top-chatters",
    response_model=list[list[Any]],
    summary="Get a creator's most active chatters",
    description="Return [chatter_id, nick, message_count] rows across all streams for one creator.",
    responses={429: {"model": ErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.GENERAL)
def get_creator_top_chatters(
    request: Request,
    response: Response,
    creator_id: int = Path(..., description="Unique creator ID", json_schema_extra={"example": 5}),
    limit: int = Query(25, ge=1, le=200, description="Maximum number of chatters to return", json_schema_extra={"example": 25}),
) -> list[list[Any]]:
    """Get the most active chatters across a creator's streams."""
    try:
        cache = get_cache()
        cache_key = cache._generate_key("creator_top_chatters", creator_id, limit)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "creator_top_chatters")
            return cast(list[list[Any]], cached_result)

        record_cache_operation("miss", "creator_top_chatters")
        result = select_creator_top_chatters_db(creator_id, limit)
        cache.set(cache_key, result, CacheTTL.STREAM_DETAILS)
        record_cache_operation("set", "creator_top_chatters")
        response.headers["X-Cache"] = "MISS"
        return cast(list[list[Any]], result)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error fetching creator top chatters: {exc}")
        record_cache_operation("error", "creator_top_chatters")
        raise HTTPException(status_code=500, detail="Internal server error")
