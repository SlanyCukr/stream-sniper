"""Read-only per-stream/creator insight endpoints (mentions, emotes, phrases)."""

from typing import Any, cast

from fastapi import APIRouter, HTTPException, Path, Query, Request, Response

from ..database.stream_emote_stats_table_gateway import (
    select_creator_emotes_db,
    select_stream_emotes_db,
)
from ..database.stream_phrase_stats_table_gateway import select_stream_phrases_db
from ..database.stream_table_gateway import select_stream_mentions_db
from ..logging_config import get_logger
from .cache import CacheTTL, get_cache
from .export_utils import csv_response
from .models import ErrorResponse
from .monitoring import record_cache_operation
from .rate_limiter import limiter, rate_limits
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


@router.get(
    "/stream/{stream_id}/mentions",
    response_model=StreamMentions,
    summary="Get @mention analytics for a stream",
    description="Most-mentioned chatters and the top directed mention pairs for one stream.",
    responses={429: {"model": ErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.ANALYTICS)
def get_stream_mentions(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1}),
    limit: int = Query(20, ge=1, le=100, description="Max mentioned chatters to return"),
    format: str = Query("json", pattern="^(json|csv)$", description="Response format"),
) -> Any:
    """Empty when no @mentions were recorded — always 200, never 404."""
    try:
        cache = get_cache()
        cache_key = cache._generate_key("stream_mentions", stream_id, limit)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "stream_mentions")
            payload = cast(dict[str, Any], cached_result)
        else:
            record_cache_operation("miss", "stream_mentions")
            mentioned_rows, pair_rows = select_stream_mentions_db(stream_id, limit)

            result = StreamMentions(
                mentioned=[
                    MentionedChatter(chatter_id=row[0], nick=row[1], count=row[2])
                    for row in mentioned_rows
                ],
                pairs=[
                    MentionPair(
                        from_chatter_id=row[0],
                        from_nick=row[1],
                        to_chatter_id=row[2],
                        to_nick=row[3],
                        count=row[4],
                    )
                    for row in pair_rows
                ],
            )
            payload = result.model_dump()
            cache.set(cache_key, payload, CacheTTL.STREAM_DETAILS)
            record_cache_operation("set", "stream_mentions")
            response.headers["X-Cache"] = "MISS"

        if format == "csv":
            return csv_response(
                ["chatter_id", "nick", "count"],
                payload["mentioned"],
                f"stream_{stream_id}_mentions.csv",
                extra_headers={"X-Cache": response.headers["X-Cache"]},
            )
        return payload
    except Exception as exc:
        logger.error(f"Error fetching stream mentions: {exc}")
        record_cache_operation("error", "stream_mentions")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/stream/{stream_id}/emotes",
    response_model=StreamEmotes,
    summary="Get top emotes for a stream",
    description="Rollup-computed emote usage (BTTV + Twitch) for one stream.",
    responses={429: {"model": ErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.ANALYTICS)
def get_stream_emotes(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1}),
    limit: int = Query(25, ge=1, le=100, description="Max emotes to return"),
    format: str = Query("json", pattern="^(json|csv)$", description="Response format"),
) -> Any:
    """Empty when the stream has no emote rollup yet — always 200, never 404."""
    try:
        cache = get_cache()
        cache_key = cache._generate_key("stream_emotes", stream_id, limit)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "stream_emotes")
            payload = cast(dict[str, Any], cached_result)
        else:
            record_cache_operation("miss", "stream_emotes")
            rows = select_stream_emotes_db(stream_id, limit)

            result = StreamEmotes(
                emotes=[
                    EmoteStat(
                        name=row[0],
                        source=row[1],
                        provider_id=row[2],
                        usage_count=row[3],
                        chatter_count=row[4],
                    )
                    for row in rows
                ]
            )
            payload = result.model_dump()
            cache.set(cache_key, payload, CacheTTL.STREAM_ANALYTICS)
            record_cache_operation("set", "stream_emotes")
            response.headers["X-Cache"] = "MISS"

        if format == "csv":
            return csv_response(
                ["name", "source", "provider_id", "usage_count", "chatter_count"],
                payload["emotes"],
                f"stream_{stream_id}_emotes.csv",
                extra_headers={"X-Cache": response.headers["X-Cache"]},
            )
        return payload
    except Exception as exc:
        logger.error(f"Error fetching stream emotes: {exc}")
        record_cache_operation("error", "stream_emotes")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/stream/{stream_id}/phrases",
    response_model=StreamPhrases,
    summary="Get recurring phrases for a stream",
    description="Rollup-computed recurring 1-2 gram phrases for one stream.",
    responses={429: {"model": ErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.ANALYTICS)
def get_stream_phrases(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Unique stream ID", json_schema_extra={"example": 1}),
    limit: int = Query(25, ge=1, le=100, description="Max phrases to return"),
    format: str = Query("json", pattern="^(json|csv)$", description="Response format"),
) -> Any:
    """Empty when the stream has no phrase rollup yet — always 200, never 404."""
    try:
        cache = get_cache()
        cache_key = cache._generate_key("stream_phrases", stream_id, limit)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "stream_phrases")
            payload = cast(dict[str, Any], cached_result)
        else:
            record_cache_operation("miss", "stream_phrases")
            rows = select_stream_phrases_db(stream_id, limit)

            result = StreamPhrases(
                phrases=[
                    PhraseStat(phrase=row[0], usage_count=row[1], chatter_count=row[2]) for row in rows
                ]
            )
            payload = result.model_dump()
            cache.set(cache_key, payload, CacheTTL.STREAM_ANALYTICS)
            record_cache_operation("set", "stream_phrases")
            response.headers["X-Cache"] = "MISS"

        if format == "csv":
            return csv_response(
                ["phrase", "usage_count", "chatter_count"],
                payload["phrases"],
                f"stream_{stream_id}_phrases.csv",
                extra_headers={"X-Cache": response.headers["X-Cache"]},
            )
        return payload
    except Exception as exc:
        logger.error(f"Error fetching stream phrases: {exc}")
        record_cache_operation("error", "stream_phrases")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/creator/{creator_id}/emotes",
    response_model=CreatorEmotes,
    summary="Get top emotes for a creator",
    description="Emote usage summed across all of a creator's streams.",
    responses={429: {"model": ErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.ANALYTICS)
def get_creator_emotes(
    request: Request,
    response: Response,
    creator_id: int = Path(..., description="Unique creator ID", json_schema_extra={"example": 1}),
    limit: int = Query(25, ge=1, le=100, description="Max emotes to return"),
) -> dict[str, Any]:
    """Empty when the creator has no emote rollups yet — always 200, never 404."""
    try:
        cache = get_cache()
        cache_key = cache._generate_key("creator_emotes", creator_id, limit)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "creator_emotes")
            return cast(dict[str, Any], cached_result)

        record_cache_operation("miss", "creator_emotes")
        rows = select_creator_emotes_db(creator_id, limit)

        result = CreatorEmotes(
            emotes=[
                CreatorEmoteStat(
                    name=row[0],
                    source=row[1],
                    provider_id=row[2],
                    usage_count=row[3],
                    chatter_count=row[4],
                    stream_count=row[5],
                )
                for row in rows
            ]
        )
        payload = result.model_dump()
        cache.set(cache_key, payload, CacheTTL.STREAM_ANALYTICS)
        record_cache_operation("set", "creator_emotes")
        response.headers["X-Cache"] = "MISS"
        return payload
    except Exception as exc:
        logger.error(f"Error fetching creator emotes: {exc}")
        record_cache_operation("error", "creator_emotes")
        raise HTTPException(status_code=500, detail="Internal server error")
