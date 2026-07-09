"""
Processing-job administration endpoints: job listing, manual VOD queueing,
and job cancel/retry controls.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from ..collector.twitch_api import TwitchAPI
from ..database.processing_jobs_table_gateway import (
    count_processing_jobs_db,
    insert_processing_job_db,
    job_exists_db,
    select_processing_job_by_id_db,
    select_processing_jobs_db,
)
from ..database.stream_table_gateway import select_stream_by_twitch_id_db
from ..database.tracked_streamers_table_gateway import select_tracked_streamer_by_id_db
from ..logging_config import get_logger
from ..tracking.scheduler import get_scheduler
from .auth import UserInDB, get_current_admin_user
from .rate_limiter import limiter
from .tracking_models import ProcessingJobsResponse, convert_processing_job_to_response

logger = get_logger(__name__)

# Mounted under /admin/tracking by tracking_router.py.
router = APIRouter()


@router.get(
    "/jobs",
    response_model=ProcessingJobsResponse,
    summary="Get processing jobs",
    description="""
    Get list of processing jobs with optional filtering and pagination.

    Requires admin role.

    **Rate Limit**: 30 requests per minute
    """,
    responses={
        200: {"description": "List of processing jobs"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("30/minute")
def get_processing_jobs(
    request: Request,
    response: Response,
    offset: int = Query(0, description="Pagination offset", ge=0),
    limit: int = Query(100, description="Page size", ge=1, le=1000),
    # Aliased so the local name doesn't shadow fastapi.status in this scope.
    job_status: Optional[str] = Query(None, alias="status", description="Filter by job status"),
    tracked_streamer_id: Optional[int] = Query(None, description="Filter by streamer ID"),
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Get processing jobs (admin only)"""
    try:
        jobs_tuple = select_processing_jobs_db(
            limit=limit,
            offset=offset,
            status=job_status,
            tracked_streamer_id=tracked_streamer_id
        )

        total = count_processing_jobs_db(
            status=job_status,
            tracked_streamer_id=tracked_streamer_id
        )

        jobs = [convert_processing_job_to_response(job_tuple)
                for job_tuple in jobs_tuple]

        return ProcessingJobsResponse(
            jobs=jobs,
            total=total,
            offset=offset,
            limit=limit
        )

    except Exception as e:
        logger.error(f"Error fetching processing jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/streamers/{streamer_id}/process",
    summary="Manually trigger processing",
    description="""
    Manually trigger processing for a tracked streamer's latest stream.

    Requires admin role.

    **Rate Limit**: 5 requests per minute
    """,
    responses={
        200: {"description": "Processing triggered successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"description": "Streamer not found"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("5/minute")
async def trigger_processing(
    streamer_id: int,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """
    Queue the streamer's newest not-yet-collected VOD for processing (admin only).

    Finds the most recent archived VOD that isn't already in the database and
    enqueues a processing job for it. The tracking service's processing queue
    picks the job up and runs the collector (bounded to that single VOD).
    Trigger repeatedly to walk back through older un-collected VODs.
    """
    try:
        # Check if streamer exists
        streamer_tuple = select_tracked_streamer_by_id_db(streamer_id)
        if not streamer_tuple:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tracked streamer not found"
            )

        twitch_username = streamer_tuple[2]

        # List archived VODs from Twitch (newest first).
        try:
            twitch_api = TwitchAPI()
            await twitch_api.twitch_api_init()
            twitch_api.set_streamer_nickname(twitch_username)
            videos = await twitch_api.get_available_video_ids_async()
        except Exception as e:
            logger.error(f"Failed to list VODs for {twitch_username}: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to list VODs from Twitch"
            )

        # Pick the newest VOD not already collected into the stream table.
        target = next(
            (v for v in videos if not select_stream_by_twitch_id_db(int(v.id))),
            None
        )
        if target is None:
            return {"message": "No un-collected VODs available for this streamer", "queued": False}

        twitch_stream_id = int(target.id)
        if job_exists_db(streamer_id, twitch_stream_id):
            return {
                "message": "A job for this VOD is already queued",
                "queued": False,
                "twitch_stream_id": twitch_stream_id,
            }

        job_id = insert_processing_job_db(streamer_id, twitch_stream_id)
        if not job_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create processing job"
            )

        logger.info(
            f"Manual processing queued by admin {current_user.username}: "
            f"streamer_id={streamer_id}, job_id={job_id}, vod={twitch_stream_id}"
        )
        return {
            "message": "Processing queued",
            "queued": True,
            "job_id": job_id,
            "twitch_stream_id": twitch_stream_id,
            "vod_title": target.title,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/jobs/{job_id}/cancel",
    summary="Cancel processing job",
    description="""
    Cancel a specific processing job.

    Requires admin role.

    **Rate Limit**: 10 requests per minute
    """,
    responses={
        200: {"description": "Job cancelled successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"description": "Job not found"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("10/minute")
async def cancel_job(
    job_id: int,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Cancel processing job (admin only)"""
    try:
        # Check if job exists
        job_tuple = select_processing_job_by_id_db(job_id)
        if not job_tuple:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        scheduler = get_scheduler()
        success = await scheduler.cancel_job(job_id)

        if success:
            logger.info(f"Job {job_id} cancelled by admin {current_user.username}")
            return {"message": "Job cancelled successfully"}
        else:
            return {"message": "Job was not actively running"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/jobs/{job_id}/retry",
    summary="Retry processing job",
    description="""
    Retry a failed processing job.

    Requires admin role.

    **Rate Limit**: 10 requests per minute
    """,
    responses={
        200: {"description": "Job queued for retry"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"description": "Job not found"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("10/minute")
async def retry_job(
    job_id: int,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Retry processing job (admin only)"""
    try:
        # Check if job exists
        job_tuple = select_processing_job_by_id_db(job_id)
        if not job_tuple:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        scheduler = get_scheduler()
        success = await scheduler.retry_job(job_id)

        if success:
            logger.info(f"Job {job_id} queued for retry by admin {current_user.username}")
            return {"message": "Job queued for retry"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to queue job for retry"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
