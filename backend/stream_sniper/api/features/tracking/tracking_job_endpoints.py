"""
Processing-job administration endpoints: job listing, manual VOD queueing,
and job cancel/retry controls.
"""

import asyncio
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from stream_sniper.application.tracking.job_admin import (
    ProcessingJobConflictError,
    ProcessingJobNotFoundError,
    list_processing_jobs,
    request_processing_job_cancellation,
    retry_processing_job,
)
from stream_sniper.application.tracking.manual_processing import (
    ArchivedVod,
    enqueue_first_uncollected_vod,
    load_processing_streamer,
)
from stream_sniper.application.tracking.models import (
    JobStatus,
)
from stream_sniper.collector.twitch_api import TwitchConfigurationError, TwitchUpstreamError

from ....logging_config import get_logger, sanitize_log_value
from ...dependencies import get_twitch_client
from ...security.auth import get_current_admin_user
from ...security.auth_models import UserInDB
from ...security.rate_limiter import limiter
from ...transport.models import ErrorResponse, MessageResponse, RateLimitErrorResponse
from .tracking_models import ProcessingJobsResponse, ProcessingTriggerResponse, convert_processing_job_to_response

logger = get_logger(__name__)

router = APIRouter()


@router.get(
    "/jobs",
    response_model=ProcessingJobsResponse,
    summary="Get processing jobs",
    description="Filterable by status and tracked streamer, with offset pagination.",
    responses={
        200: {"description": "List of processing jobs"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Processing-job persistence failed"},
    },
)
@limiter.limit("30/minute")
def get_processing_jobs(
    request: Request,
    response: Response,
    offset: int = Query(0, description="Pagination offset", ge=0),
    limit: int = Query(100, description="Page size", ge=1, le=1000),
    # Aliased so the local name doesn't shadow fastapi.status in this scope.
    job_status: JobStatus | None = Query(None, alias="status", description="Filter by job status"),
    tracked_streamer_id: int | None = Query(None, description="Filter by streamer ID"),
) -> ProcessingJobsResponse:
    page = list_processing_jobs(
        limit=limit,
        offset=offset,
        status=job_status,
        tracked_streamer_id=tracked_streamer_id,
    )
    jobs = [convert_processing_job_to_response(job) for job in page.jobs]
    return ProcessingJobsResponse(jobs=jobs, total=page.total, offset=offset, limit=limit)


@router.post(
    "/streamers/{streamer_id}/process",
    response_model=ProcessingTriggerResponse,
    summary="Request VOD processing",
    description="Evaluate the newest archived VOD and queue it when eligible.",
    responses={
        200: {"description": "Processing request evaluated; inspect outcome"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
        404: {"model": ErrorResponse, "description": "Streamer not found"},
        502: {"model": ErrorResponse, "description": "Twitch VOD listing failed"},
        503: {"model": ErrorResponse, "description": "Twitch integration is not configured"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Processing-job persistence failed"},
    },
)
@limiter.limit("5/minute")
async def trigger_processing(
    streamer_id: int, request: Request, response: Response, current_user: UserInDB = Depends(get_current_admin_user)
) -> ProcessingTriggerResponse:
    streamer = await asyncio.to_thread(load_processing_streamer, streamer_id)
    if not streamer:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tracked streamer not found")

    twitch_username = streamer.twitch_username

    try:
        twitch_api = get_twitch_client(request)
        await twitch_api.ensure_initialized()
        videos = await twitch_api.get_archived_videos(twitch_username)
    except TwitchConfigurationError as error:
        logger.exception("Twitch integration is not configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Twitch lookups aren't available right now because the server's Twitch access isn't configured. Contact the administrator."
        ) from error
    except TwitchUpstreamError as error:
        logger.exception("Failed to list VODs for %s", sanitize_log_value(twitch_username))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not fetch recent VODs from Twitch. Try again in a moment.",
        ) from error

    outcome = await asyncio.to_thread(enqueue_first_uncollected_vod, streamer_id, videos)
    if outcome.status == "no_vod":
        return ProcessingTriggerResponse(
            outcome="no_vod",
            message="No un-collected VODs available for this streamer",
            queued=False,
        )

    target = cast(ArchivedVod, outcome.video)
    twitch_vod_id = int(target.twitch_vod_id)
    if outcome.status == "already_queued":
        return ProcessingTriggerResponse(
            outcome="already_queued",
            message="A job for this VOD is already queued",
            queued=False,
            twitch_vod_id=twitch_vod_id,
        )

    logger.info(
        "Manual processing queued by admin %s: streamer_id=%s, job_id=%s, vod=%s",
        sanitize_log_value(current_user.username),
        streamer_id,
        outcome.job_id,
        twitch_vod_id,
    )
    return ProcessingTriggerResponse(
        outcome="queued",
        message="Processing queued",
        queued=True,
        job_id=outcome.job_id,
        twitch_vod_id=twitch_vod_id,
        vod_title=target.title,
    )


@router.post(
    "/jobs/{job_id}/cancel",
    response_model=MessageResponse,
    summary="Request processing-job cancellation",
    responses={
        200: {"description": "Cancellation request accepted"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
        404: {"model": ErrorResponse, "description": "Job not found"},
        409: {"model": ErrorResponse, "description": "Job already finished"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Processing-job persistence failed"},
    },
)
@limiter.limit("10/minute")
async def cancel_job(
    job_id: int, request: Request, response: Response, current_user: UserInDB = Depends(get_current_admin_user)
) -> MessageResponse:
    try:
        await asyncio.to_thread(request_processing_job_cancellation, job_id)
    except ProcessingJobNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    except ProcessingJobConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    logger.info("Job %s cancellation requested by admin %s", job_id, sanitize_log_value(current_user.username))
    return MessageResponse(message="Job cancellation requested")


@router.post(
    "/jobs/{job_id}/retry",
    response_model=MessageResponse,
    summary="Retry processing job",
    description="Only failed jobs can transition back to queued.",
    responses={
        200: {"description": "Job queued for retry"},
        401: {"model": ErrorResponse, "description": "Authentication required"},
        403: {"model": ErrorResponse, "description": "Admin role required"},
        404: {"model": ErrorResponse, "description": "Job not found"},
        409: {"model": ErrorResponse, "description": "Job is not retryable or changed concurrently"},
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
        500: {"model": ErrorResponse, "description": "Processing-job persistence failed"},
    },
)
@limiter.limit("10/minute")
async def retry_job(
    job_id: int, request: Request, response: Response, current_user: UserInDB = Depends(get_current_admin_user)
) -> MessageResponse:
    try:
        await asyncio.to_thread(retry_processing_job, job_id)
    except ProcessingJobNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    except ProcessingJobConflictError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    logger.info("Job %s queued for retry by admin %s", job_id, sanitize_log_value(current_user.username))
    return MessageResponse(message="Job queued for retry")
