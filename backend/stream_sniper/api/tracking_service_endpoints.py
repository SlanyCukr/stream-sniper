"""
Tracking service telemetry and lifecycle endpoints: aggregate statistics,
live status, and start/stop/restart controls for the scheduler.
"""

import asyncio
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from ..database.processing_jobs_table_gateway import get_processing_stats_db
from ..database.tracked_streamers_table_gateway import count_tracked_streamers_db
from ..logging_config import get_logger
from ..tracking.heartbeat import read_heartbeat
from ..tracking.scheduler import get_scheduler
from .auth import UserInDB, get_current_admin_user
from .rate_limiter import limiter
from .tracking_models import TrackingStatsResponse

logger = get_logger(__name__)

# Mounted under /admin/tracking by tracking_router.py.
router = APIRouter()


def _live_tracking_status() -> tuple[Dict[str, Any], bool]:
    """Resolve the tracking system's real status across processes.

    The scheduler singleton is per-process; in the standard deployment monitoring
    runs in the separate ``stream-sniper-tracking`` container, so this (API)
    process's own singleton is never started and would always look 'down'. Prefer
    the heartbeat the tracking process publishes to Postgres; fall back to this
    process's scheduler, which covers running it in-process (local single-process
    runs or ``POST /service/start``).

    Returns the status dict (same shape as ``TrackingScheduler.get_status()``)
    and whether that source is actually alive.
    """
    hb = read_heartbeat()
    if hb and hb.get("alive"):
        return hb["status"], True

    status_dict = get_scheduler().get_status()
    in_proc_alive = bool(status_dict.get("scheduler", {}).get("running"))
    return status_dict, in_proc_alive


@router.get(
    "/stats",
    response_model=TrackingStatsResponse,
    summary="Get tracking statistics",
    description="""
    Get comprehensive tracking system statistics.

    Requires admin role.

    **Rate Limit**: 30 requests per minute
    """,
    responses={
        200: {"description": "Tracking statistics"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("30/minute")
def get_tracking_stats(
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Get tracking statistics (admin only)"""
    try:
        # Get tracked streamers stats
        total_streamers = count_tracked_streamers_db()
        active_streamers = count_tracked_streamers_db(is_active=True)
        processing_enabled_streamers = count_tracked_streamers_db(processing_enabled=True)

        streamers_stats = {
            'total': total_streamers,
            'active': active_streamers,
            'processing_enabled': processing_enabled_streamers,
            'inactive': total_streamers - active_streamers
        }

        # Get processing jobs stats
        jobs_stats = get_processing_stats_db()

        # Get system status — prefer the tracking process's Postgres heartbeat, since
        # monitoring runs in a separate container from the API (whose in-process
        # scheduler singleton is never started and would always read as 'down').
        tracking_status, source_alive = _live_tracking_status()
        monitor_status = tracking_status.get('stream_monitor', {})
        scheduler_info = tracking_status.get('scheduler', {})
        queue_status = tracking_status.get('processing_queue', {})

        system_status = {
            'monitoring_active': source_alive and bool(monitor_status.get('running')),
            'processing_queue_size': jobs_stats.get('pending', 0),
            'failed_jobs': jobs_stats.get('failed', 0),
            'scheduler_running': source_alive and bool(scheduler_info.get('running')),
            'active_jobs': queue_status.get('active_jobs', 0),
            'uptime_seconds': scheduler_info.get('uptime_seconds')
        }

        return TrackingStatsResponse(
            tracked_streamers=streamers_stats,
            processing_jobs=jobs_stats,
            system_status=system_status
        )

    except Exception as e:
        logger.error(f"Error fetching tracking stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/service/status",
    summary="Get tracking service status",
    description="""
    Get detailed status of the tracking service including scheduler, monitor, and queue.

    Requires admin role.

    **Rate Limit**: 60 requests per minute
    """,
    responses={
        200: {"description": "Service status"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("60/minute")
def get_service_status(
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Get tracking service status (admin only)"""
    try:
        # Reflect the real (possibly separate-container) tracking process via its
        # Postgres heartbeat, falling back to this process's scheduler.
        tracking_status, _ = _live_tracking_status()
        return tracking_status
    except Exception as e:
        logger.error(f"Error getting service status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/service/start",
    summary="Start tracking service",
    description="""
    Start the tracking service if it's not already running.

    Requires admin role.

    **Rate Limit**: 5 requests per minute
    """,
    responses={
        200: {"description": "Service started successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("5/minute")
async def start_service(
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Start tracking service (admin only)"""
    try:
        scheduler = get_scheduler()

        if scheduler.is_running():
            return {"message": "Service is already running"}

        # Start the service in the background
        asyncio.create_task(scheduler.start())

        logger.info(f"Tracking service started by admin {current_user.username}")
        return {"message": "Service started successfully"}

    except Exception as e:
        logger.error(f"Error starting service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/service/stop",
    summary="Stop tracking service",
    description="""
    Stop the tracking service if it's running.

    Requires admin role.

    **Rate Limit**: 5 requests per minute
    """,
    responses={
        200: {"description": "Service stopped successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("5/minute")
async def stop_service(
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Stop tracking service (admin only)"""
    try:
        scheduler = get_scheduler()

        if not scheduler.is_running():
            return {"message": "Service is not running"}

        await scheduler.stop()

        logger.info(f"Tracking service stopped by admin {current_user.username}")
        return {"message": "Service stopped successfully"}

    except Exception as e:
        logger.error(f"Error stopping service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/service/restart",
    summary="Restart tracking service",
    description="""
    Restart the tracking service.

    Requires admin role.

    **Rate Limit**: 5 requests per minute
    """,
    responses={
        200: {"description": "Service restarted successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("5/minute")
async def restart_service(
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Restart tracking service (admin only)"""
    try:
        scheduler = get_scheduler()

        # Restart the service in the background
        asyncio.create_task(scheduler.restart())

        logger.info(f"Tracking service restarted by admin {current_user.username}")
        return {"message": "Service restarted successfully"}

    except Exception as e:
        logger.error(f"Error restarting service: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
