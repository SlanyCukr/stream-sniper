"""Read-only per-stream/creator insight endpoints (mentions, emotes, phrases)."""

from fastapi import APIRouter, Path, Query, Request, Response

from ....database.gateways.analytics.stream_emote_stats_table_gateway import (
    select_creator_emotes_db,
    select_stream_emotes_db,
)
from ....database.gateways.analytics.stream_phrase_stats_table_gateway import select_stream_phrases_db
from ....database.gateways.streams.stream_table_gateway import select_stream_mentions_db
from ....logging_config import get_logger
from ...caching.cache import CacheTTL
from ...caching.model_cache import ModelCachePolicy
from ...dependencies import get_cache
from ...security.rate_limiter import limiter, rate_limits
from ...transport.export_utils import csv_response
from ...transport.models import RateLimitErrorResponse
from .stream_insight_models import (
    CreatorEmotes,
    CreatorEmoteStat,
    EmoteStat,
    MentionedChatter,
    MentionPair,
    PhraseStat,
    StreamEmotes,
    StreamMentions,
    StreamPhrases,
)

logger = get_logger(__name__)

router = APIRouter(tags=["Stream Insights"])

_MENTIONS_CACHE = ModelCachePolicy("stream_mentions", CacheTTL.STREAM_DETAILS, StreamMentions)
_STREAM_EMOTES_CACHE = ModelCachePolicy("stream_emotes", CacheTTL.STREAM_ANALYTICS, StreamEmotes)
_PHRASES_CACHE = ModelCachePolicy("stream_phrases", CacheTTL.STREAM_ANALYTICS, StreamPhrases)
_CREATOR_EMOTES_CACHE = ModelCachePolicy("creator_emotes", CacheTTL.STREAM_ANALYTICS, CreatorEmotes)


def _load_stream_mentions(request: Request, response: Response, stream_id: int, limit: int) -> StreamMentions:
    cache = get_cache(request)
    cache_key, cached_result = _MENTIONS_CACHE.lookup(cache, response, stream_id, limit)
    if cached_result is not None:
        return cached_result

    mentioned_rows, pair_rows = select_stream_mentions_db(stream_id, limit)
    result = StreamMentions(
        mentioned=[
            MentionedChatter(chatter_id=row.chatter_id, nick=row.nick, count=row.mention_count)
            for row in mentioned_rows
        ],
        pairs=[
            MentionPair(
                from_chatter_id=row.from_chatter_id,
                from_nick=row.from_nick,
                to_chatter_id=row.to_chatter_id,
                to_nick=row.to_nick,
                count=row.pair_count,
            )
            for row in pair_rows
        ],
    )
    _MENTIONS_CACHE.store(cache, response, cache_key, result)
    return result


@router.get(
    "/streams/{stream_id}/mentions",
    response_model=StreamMentions,
    summary="Get @mention analytics for a stream",
    description="Most-mentioned chatters and the top directed mention pairs for one stream.",
    responses={429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.ANALYTICS)
def get_stream_mentions(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1}),
    limit: int = Query(20, ge=1, le=100, description="Max mentioned chatters to return"),
) -> StreamMentions:
    """Empty when no @mentions were recorded — always 200, never 404."""
    with _MENTIONS_CACHE.record_failures():
        return _load_stream_mentions(request, response, stream_id, limit)


def _load_stream_emotes(request: Request, response: Response, stream_id: int, limit: int) -> StreamEmotes:
    cache = get_cache(request)
    cache_key, cached_result = _STREAM_EMOTES_CACHE.lookup(cache, response, stream_id, limit)
    if cached_result is not None:
        return cached_result

    rows = select_stream_emotes_db(stream_id, limit)
    result = StreamEmotes(
        emotes=[
            EmoteStat(
                name=row.name,
                source=row.source,
                provider_id=row.provider_id,
                usage_count=row.usage_count,
                chatter_count=row.chatter_count,
            )
            for row in rows
        ]
    )
    _STREAM_EMOTES_CACHE.store(cache, response, cache_key, result)
    return result


@router.get(
    "/streams/{stream_id}/emotes",
    response_model=StreamEmotes,
    summary="Get top emotes for a stream",
    description="Rollup-computed emote usage (BTTV + Twitch) for one stream.",
    responses={429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.ANALYTICS)
def get_stream_emotes(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1}),
    limit: int = Query(25, ge=1, le=100, description="Max emotes to return"),
) -> StreamEmotes:
    """Empty when the stream has no emote rollup yet — always 200, never 404."""
    with _STREAM_EMOTES_CACHE.record_failures():
        return _load_stream_emotes(request, response, stream_id, limit)


def _load_stream_phrases(request: Request, response: Response, stream_id: int, limit: int) -> StreamPhrases:
    cache = get_cache(request)
    cache_key, cached_result = _PHRASES_CACHE.lookup(cache, response, stream_id, limit)
    if cached_result is not None:
        return cached_result

    rows = select_stream_phrases_db(stream_id, limit)
    result = StreamPhrases(
        phrases=[
            PhraseStat(phrase=row.phrase, usage_count=row.usage_count, chatter_count=row.chatter_count) for row in rows
        ]
    )
    _PHRASES_CACHE.store(cache, response, cache_key, result)
    return result


@router.get(
    "/streams/{stream_id}/phrases",
    response_model=StreamPhrases,
    summary="Get recurring phrases for a stream",
    description="Rollup-computed recurring 1-2 gram phrases for one stream.",
    responses={429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.ANALYTICS)
def get_stream_phrases(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1}),
    limit: int = Query(25, ge=1, le=100, description="Max phrases to return"),
) -> StreamPhrases:
    """Empty when the stream has no phrase rollup yet — always 200, never 404."""
    with _PHRASES_CACHE.record_failures():
        return _load_stream_phrases(request, response, stream_id, limit)


@router.get("/streams/{stream_id}/mentions/export", summary="Export stream mentions as CSV")
@limiter.limit(rate_limits.ANALYTICS)
def export_stream_mentions(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID"),
    limit: int = Query(20, ge=1, le=100),
) -> Response:
    result = _load_stream_mentions(request, response, stream_id, limit)
    return csv_response(
        ["chatter_id", "nick", "count"],
        [item.model_dump() for item in result.mentioned],
        f"stream_{stream_id}_mentions.csv",
        extra_headers={"X-Cache": response.headers["X-Cache"]},
    )


@router.get("/streams/{stream_id}/emotes/export", summary="Export stream emotes as CSV")
@limiter.limit(rate_limits.ANALYTICS)
def export_stream_emotes(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID"),
    limit: int = Query(25, ge=1, le=100),
) -> Response:
    result = _load_stream_emotes(request, response, stream_id, limit)
    return csv_response(
        ["name", "source", "provider_id", "usage_count", "chatter_count"],
        [item.model_dump() for item in result.emotes],
        f"stream_{stream_id}_emotes.csv",
        extra_headers={"X-Cache": response.headers["X-Cache"]},
    )


@router.get("/streams/{stream_id}/phrases/export", summary="Export stream phrases as CSV")
@limiter.limit(rate_limits.ANALYTICS)
def export_stream_phrases(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID"),
    limit: int = Query(25, ge=1, le=100),
) -> Response:
    result = _load_stream_phrases(request, response, stream_id, limit)
    return csv_response(
        ["phrase", "usage_count", "chatter_count"],
        [item.model_dump() for item in result.phrases],
        f"stream_{stream_id}_phrases.csv",
        extra_headers={"X-Cache": response.headers["X-Cache"]},
    )


@router.get(
    "/creators/{creator_id}/emotes",
    response_model=CreatorEmotes,
    summary="Get top emotes for a creator",
    description="Emote usage summed across all of a creator's streams.",
    responses={429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.ANALYTICS)
def get_creator_emotes(
    request: Request,
    response: Response,
    creator_id: int = Path(..., description="Unique creator ID", json_schema_extra={"example": 1}),
    limit: int = Query(25, ge=1, le=100, description="Max emotes to return"),
) -> CreatorEmotes:
    """Empty when the creator has no emote rollups yet — always 200, never 404."""
    with _CREATOR_EMOTES_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _CREATOR_EMOTES_CACHE.lookup(cache, response, creator_id, limit)
        if cached_result is not None:
            return cached_result

        rows = select_creator_emotes_db(creator_id, limit)

        result = CreatorEmotes(
            emotes=[
                CreatorEmoteStat(
                    name=row.name,
                    source=row.source,
                    provider_id=row.provider_id,
                    usage_count=row.usage_count,
                    chatter_count=row.chatter_count,
                    stream_count=row.stream_count,
                )
                for row in rows
            ]
        )
        _CREATOR_EMOTES_CACHE.store(cache, response, cache_key, result)
        return result
