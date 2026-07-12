"""Highlight-queue endpoints: read the moment queue; curate moments (admin only)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response

from ..database.moment_review_table_gateway import (
    delete_moment_review_db,
    upsert_moment_review_db,
)
from ..database.stream_moment_table_gateway import (
    select_moment_exists_db,
    select_moment_queue_db,
)
from ..logging_config import get_logger
from .auth import UserInDB, get_current_admin_user
from .cache import CacheTTL, get_cache, invalidate_cache_pattern
from .models import ErrorResponse
from .moment_models import (
    MomentQueue,
    MomentQueueItem,
    MomentReviewRequest,
    MomentReviewResponse,
)
from .monitoring import record_cache_operation
from .rate_limiter import limiter, rate_limits

logger = get_logger(__name__)

router = APIRouter(tags=["Moments"])


def _invalidate_moment_caches() -> None:
    """Drop cached timeline, queue and report pages so a curation change is reflected immediately."""
    invalidate_cache_pattern("stream_timeline:*")
    invalidate_cache_pattern("moments_queue:*")
    # The report card embeds top_moments filtered by review status.
    invalidate_cache_pattern("stream_report:*")


@router.get(
    "/moments",
    response_model=MomentQueue,
    summary="Get the highlight queue",
    description="Enriched moments across streams, filterable by review status and creator.",
    responses={
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.ANALYTICS)
def get_moment_queue(
    request: Request,
    response: Response,
    status: str = Query("", pattern="^(pending|bookmarked|rejected|)$"),
    creator_id: Optional[int] = Query(None, description="Restrict to one creator", ge=1),
    limit: int = Query(50, description="Page size", ge=1, le=200),
    offset: int = Query(0, description="Page offset", ge=0),
) -> MomentQueue:
    """Get a page of the highlight queue.

    `status=""` (default) returns every moment; `pending` means no review row exists.
    """
    try:
        cache = get_cache()
        cache_key = cache._generate_key("moments_queue", status, creator_id, limit, offset)
        cached_result = cache.get(cache_key)
        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "moments_queue")
            return MomentQueue(**cached_result)

        record_cache_operation("miss", "moments_queue")
        rows, total = select_moment_queue_db(status, creator_id, limit, offset)

        items = [
            MomentQueueItem(
                stream_id=row[0],
                title=row[1],
                start=row[2],
                twitch_id=row[3],
                creator_id=row[4],
                creator_display_name=row[5],
                bucket_minute=row[6],
                offset_seconds=row[7],
                message_count=row[8],
                baseline=row[9],
                ratio=row[10],
                unique_chatters=row[11],
                sub_share=row[12],
                emote_share=row[13],
                top_phrases=row[14],
                sample_messages=row[15],
                status=row[16] or "pending",
            )
            for row in rows
        ]
        result = MomentQueue(items=items, total=total, limit=limit, offset=offset)
        cache.set(cache_key, result.model_dump(), CacheTTL.STREAM_ANALYTICS)
        record_cache_operation("set", "moments_queue")
        response.headers["X-Cache"] = "MISS"
        return result
    except Exception as exc:
        logger.error(f"Error fetching moment queue: {exc}")
        record_cache_operation("error", "moments_queue")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put(
    "/stream/{stream_id}/moments/{bucket_minute}/review",
    response_model=MomentReviewResponse,
    summary="Set a moment's review status (Admin only)",
    description="Bookmark or reject a moment. Curation is global state, so admin only.",
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"model": ErrorResponse, "description": "Moment not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
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
    try:
        if not select_moment_exists_db(stream_id, bucket_minute):
            raise HTTPException(status_code=404, detail="Moment not found")

        updated_at = upsert_moment_review_db(stream_id, bucket_minute, body.status)
        _invalidate_moment_caches()
        logger.info(
            f"Moment review set by admin {current_user.username}: "
            f"stream={stream_id} bucket={bucket_minute} status={body.status}"
        )
        return MomentReviewResponse(status=body.status, updated_at=updated_at)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error setting moment review: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete(
    "/stream/{stream_id}/moments/{bucket_minute}/review",
    response_model=MomentReviewResponse,
    summary="Clear a moment's review status (Admin only)",
    description="Remove a moment's bookmark/reject decision. Admin only.",
    responses={
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"model": ErrorResponse, "description": "Moment not found"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def clear_moment_review(
    request: Request,
    response: Response,
    stream_id: int = Path(..., description="Stream ID", json_schema_extra={"example": 42}),
    bucket_minute: str = Path(..., description="Moment minute (ISO 8601)"),
    current_user: UserInDB = Depends(get_current_admin_user),
) -> MomentReviewResponse:
    """Clear a moment's review status (admin only). 404 if the moment does not exist."""
    try:
        if not select_moment_exists_db(stream_id, bucket_minute):
            raise HTTPException(status_code=404, detail="Moment not found")

        delete_moment_review_db(stream_id, bucket_minute)
        _invalidate_moment_caches()
        logger.info(
            f"Moment review cleared by admin {current_user.username}: "
            f"stream={stream_id} bucket={bucket_minute}"
        )
        return MomentReviewResponse(status=None, updated_at=None)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error clearing moment review: {exc}")
        raise HTTPException(status_code=500, detail="Internal server error")
