"""Highlight-queue endpoints: read the moment queue; curate moments (admin only)."""

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response
from fastapi import status as http_status

from stream_sniper.database.gateways.content.records import MOMENT_STATUS_PENDING, MomentQueueStatusFilter

from ....database.gateways.content.moment_review_table_gateway import (
    delete_moment_review_db,
    upsert_moment_review_db,
)
from ....database.gateways.content.stream_moment_table_gateway import (
    moment_exists_db,
    select_moment_queue_db,
)
from ....logging_config import get_logger
from ...caching.cache import CacheTTL, InProcessCache, invalidate_cache_pattern
from ...caching.model_cache import ModelCachePolicy
from ...dependencies import get_cache
from ...security.auth import get_current_admin_user
from ...security.auth_models import UserInDB
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import ErrorOrValidationResponse, ErrorResponse, RateLimitErrorResponse
from .moment_models import (
    MomentQueue,
    MomentQueueItem,
    MomentReviewRequest,
    MomentReviewResponse,
)

logger = get_logger(__name__)

router = APIRouter(tags=["Moments"])

_MOMENT_QUEUE_CACHE = ModelCachePolicy("moments_queue", CacheTTL.STREAM_ANALYTICS, MomentQueue)


def _invalidate_moment_caches(cache: InProcessCache) -> None:
    """Drop cached timeline, queue and report pages so a curation change is reflected immediately."""
    invalidate_cache_pattern(cache, "stream_timeline:*")
    invalidate_cache_pattern(cache, "moments_queue:*")
    # The report card embeds top_moments filtered by review status.
    invalidate_cache_pattern(cache, "stream_report:*")


@router.get(
    "/moments",
    response_model=MomentQueue,
    summary="Get the highlight queue",
    description="Enriched moments across streams, filterable by review status and creator.",
    responses={
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_moment_queue(
    request: Request,
    response: Response,
    status: MomentQueueStatusFilter = Query(""),
    creator_id: int | None = Query(None, description="Restrict to one creator", ge=1),
    limit: int = Query(50, description="Page size", ge=1, le=200),
    offset: int = Query(0, description="Page offset", ge=0),
) -> MomentQueue:
    """Get a page of the highlight queue.

    `status=""` (default) returns every moment; `pending` means no review row exists.
    """
    with _MOMENT_QUEUE_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached_result = _MOMENT_QUEUE_CACHE.lookup(cache, response, status, creator_id, limit, offset)
        if cached_result is not None:
            return cached_result

        rows, total = select_moment_queue_db(status, creator_id, limit, offset)

        items = [
            MomentQueueItem(
                stream_id=row.stream_id,
                title=row.title,
                start=row.start,
                twitch_vod_id=row.twitch_vod_id,
                creator_id=row.creator_id,
                creator_display_name=row.creator_display_name,
                bucket_minute=row.bucket_minute,
                offset_seconds=row.offset_seconds,
                message_count=row.message_count,
                baseline=row.baseline,
                ratio=row.ratio,
                unique_chatters=row.unique_chatters,
                sub_share=row.sub_share,
                emote_share=row.emote_share,
                top_phrases=row.top_phrases,
                sample_messages=row.sample_messages,
                status=row.status or MOMENT_STATUS_PENDING,
                clip_url=row.clip_url,
                note=row.note,
            )
            for row in rows
        ]
        result = MomentQueue(items=items, total=total, limit=limit, offset=offset)
        _MOMENT_QUEUE_CACHE.store(cache, response, cache_key, result)
        return result


@router.put(
    "/streams/{stream_id}/moments/{bucket_minute}/review",
    response_model=MomentReviewResponse,
    summary="Set a moment's review status (Admin only)",
    description="Bookmark, reject, attach a clip, or publish a moment. Admin only.",
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"model": ErrorResponse, "description": "Moment not found"},
        422: {"model": ErrorOrValidationResponse, "description": "Invalid review payload or missing clip URL"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def set_moment_review(
    body: MomentReviewRequest,
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Stream ID", json_schema_extra={"example": 42}),
    bucket_minute: str = Path(..., description="Moment minute (ISO 8601)"),
    current_user: UserInDB = Depends(get_current_admin_user),
) -> MomentReviewResponse:
    """Set a moment's review status (admin only). 404 if the moment does not exist."""
    if not moment_exists_db(stream_id, bucket_minute):
        raise HTTPException(status_code=404, detail="Moment not found")

    if body.status in {"clipped", "published"} and not body.clip_url:
        raise HTTPException(status_code=422, detail="clip_url is required for clipped/published moments")
    updated_at = upsert_moment_review_db(
        stream_id,
        bucket_minute,
        body.status,
        clip_url=body.clip_url,
        note=body.note,
    )
    _invalidate_moment_caches(get_cache(request))
    logger.info(
        f"Moment review set by admin {current_user.username}: "
        f"stream={stream_id} bucket={bucket_minute} status={body.status}"
    )
    return MomentReviewResponse(
        status=body.status,
        updated_at=updated_at,
        clip_url=body.clip_url,
        note=body.note,
    )


@router.delete(
    "/streams/{stream_id}/moments/{bucket_minute}/review",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Clear a moment's review status (Admin only)",
    description="Remove a moment's bookmark/reject decision. Admin only.",
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"model": ErrorResponse, "description": "Moment not found"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def clear_moment_review(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Stream ID", json_schema_extra={"example": 42}),
    bucket_minute: str = Path(..., description="Moment minute (ISO 8601)"),
    current_user: UserInDB = Depends(get_current_admin_user),
) -> None:
    """Clear a moment's review status (admin only). 404 if the moment does not exist."""
    if not moment_exists_db(stream_id, bucket_minute):
        raise HTTPException(status_code=404, detail="Moment not found")

    delete_moment_review_db(stream_id, bucket_minute)
    _invalidate_moment_caches(get_cache(request))
    logger.info(f"Moment review cleared by admin {current_user.username}: stream={stream_id} bucket={bucket_minute}")
    return None
