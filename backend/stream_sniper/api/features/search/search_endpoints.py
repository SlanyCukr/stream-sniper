"""Public read endpoints for scene-wide chat search."""

from fastapi import APIRouter, HTTPException, Query, Request, Response

from ....application.scenes import search_query
from ....application.scenes.search_models import (
    ContextResponse,
    FirstMatchResponse,
    FrequencyResponse,
    SearchMessagesResponse,
)
from ....logging_config import get_logger
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy
from ...dependencies import get_cache
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import ErrorOrValidationResponse, ErrorResponse, RateLimitErrorResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/search", tags=["Search"])

# Minimum is 3: pg_trgm extracts no trigrams from shorter terms, so a 1-2 char query
# cannot use the GIN index and would degrade to a public, cache-missing seq scan.
_QUERY_MIN = 3
_QUERY_MAX = 200
_FREQUENCY_MAX_DAYS = 365

_MESSAGES_CACHE = ModelCachePolicy("search_messages", CacheTTL.CHATTER_SEARCH, SearchMessagesResponse)
_FIRST_CACHE = ModelCachePolicy("search_first", CacheTTL.CHATTER_SEARCH, FirstMatchResponse)
_FREQUENCY_CACHE = ModelCachePolicy("search_frequency", CacheTTL.CHATTER_SEARCH, FrequencyResponse)
_CONTEXT_CACHE = ModelCachePolicy("search_context", CacheTTL.STREAM_DETAILS, ContextResponse)


def _clean_query(raw: str) -> str:
    """Validate and normalize the search term, or raise a plain-language 422."""
    term = raw.strip()
    if len(term) < _QUERY_MIN:
        raise HTTPException(
            status_code=422,
            detail="Search for at least 3 characters so we can find matching messages.",
        )
    if len(term) > _QUERY_MAX:
        raise HTTPException(
            status_code=422,
            detail="That search is too long. Keep it under 200 characters.",
        )
    return term


@router.get(
    "/messages",
    response_model=SearchMessagesResponse,
    summary="Search chat messages scene-wide",
    description=(
        "Case- and accent-insensitive substring search over every chat message. "
        "Results are newest-first and paginated; optionally scope to one creator or a recent window."
    ),
    responses={
        422: {"model": ErrorOrValidationResponse, "description": "Invalid search term"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def search_messages(
    request: Request,
    response: Response,
    q: str = Query(..., description="Substring to search for", json_schema_extra={"example": "pog"}),
    creator_id: int | None = Query(None, ge=1, description="Restrict to one creator"),
    days: int | None = Query(None, ge=1, description="Restrict to the last N days"),
    limit: int = Query(50, ge=1, le=100, description="Maximum hits per page"),
    offset: int = Query(0, ge=0, description="Row offset for pagination"),
) -> SearchMessagesResponse:
    """Paginated newest-first message search across the whole scene."""
    term = _clean_query(q)
    with _MESSAGES_CACHE.record_failures():
        cache = get_cache(request)
        # "all" (not 0) for the unscoped case so no conceivable creator id collides.
        cache_key, cached = _MESSAGES_CACHE.lookup(
            cache, response, term.lower(), creator_id if creator_id is not None else "all", days or 0, limit, offset
        )
        if cached is not None:
            return cached

        result = search_query.search_messages(term, creator_id, days, limit, offset)
        _MESSAGES_CACHE.store(cache, response, cache_key, result)
        return result


@router.get(
    "/first",
    response_model=FirstMatchResponse,
    summary="Find the origin of a phrase",
    description=(
        "Return the earliest matching message overall, each creator's earliest match (up to 8), "
        "and the total number of matching messages."
    ),
    responses={
        422: {"model": ErrorOrValidationResponse, "description": "Invalid search term"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def search_first(
    request: Request,
    response: Response,
    q: str = Query(..., description="Substring to search for", json_schema_extra={"example": "kekw"}),
    creator_id: int | None = Query(None, ge=1, description="Restrict to one creator"),
) -> FirstMatchResponse:
    """Trace where and when a phrase first appeared in the scene."""
    term = _clean_query(q)
    with _FIRST_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached = _FIRST_CACHE.lookup(
            cache, response, term.lower(), creator_id if creator_id is not None else "all"
        )
        if cached is not None:
            return cached

        result = search_query.find_first_match(term, creator_id)
        _FIRST_CACHE.store(cache, response, cache_key, result)
        return result


@router.get(
    "/frequency",
    response_model=FrequencyResponse,
    summary="Daily frequency of a search term",
    description="Zero-filled per-day counts of matching messages over a trailing window.",
    responses={
        422: {"model": ErrorOrValidationResponse, "description": "Invalid search term"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def search_frequency(
    request: Request,
    response: Response,
    q: str = Query(..., description="Substring to search for", json_schema_extra={"example": "gg"}),
    days: int = Query(90, ge=1, le=_FREQUENCY_MAX_DAYS, description="Length of the trailing window in days"),
    creator_id: int | None = Query(None, ge=1, description="Restrict to one creator"),
) -> FrequencyResponse:
    """Per-day mention counts for a term, zero-filled across the window."""
    term = _clean_query(q)
    with _FREQUENCY_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached = _FREQUENCY_CACHE.lookup(
            cache, response, term.lower(), days, creator_id if creator_id is not None else "all"
        )
        if cached is not None:
            return cached

        result = search_query.search_frequency(term, days, creator_id)
        _FREQUENCY_CACHE.store(cache, response, cache_key, result)
        return result


@router.get(
    "/context",
    response_model=ContextResponse,
    summary="Chat context around a matched message",
    description="Replay the messages surrounding a single message so a search hit can be read in context.",
    responses={
        404: {"model": ErrorResponse, "description": "Message not found in the given stream"},
        422: {"model": ErrorOrValidationResponse, "description": "Invalid parameter"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def search_context(
    request: Request,
    response: Response,
    stream_id: int = Query(..., description="Stream the message belongs to"),
    message_id: int = Query(..., description="Message to center the window on"),
    radius: int = Query(25, ge=1, le=100, description="Messages to show on each side of the hit"),
) -> ContextResponse:
    """Show the surrounding chat for a single message id within its stream."""
    with _CONTEXT_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached = _CONTEXT_CACHE.lookup(cache, response, stream_id, message_id, radius)
        if cached is not None:
            return cached

        try:
            result = search_query.get_search_context(stream_id, message_id, radius)
        except search_query.SearchContextNotFoundError:
            raise HTTPException(status_code=404, detail="We couldn't find that message in this stream.") from None
        _CONTEXT_CACHE.store(cache, response, cache_key, result)
        return result
