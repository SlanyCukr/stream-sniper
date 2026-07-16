"""
Tracking service telemetry endpoints backed by validated cross-process status.
"""

from fastapi import APIRouter, Request, Response

from ....database.gateways.tracking.processing_jobs_table_gateway import select_processing_stats_db
from ....database.gateways.tracking.tracked_streamers_table_gateway import count_tracked_streamers_db
from ....tracking.heartbeat import read_heartbeat
from ....tracking.status import (
    HeartbeatSnapshot,
    TrackingStatus,
    TrackingStatusSource,
    unavailable_tracking_status,
)
from ...security.rate_limiter import limiter
from ...transport.models import RateLimitErrorResponse
from .tracking_models import (
    TrackingServiceStatusResponse,
    TrackingStatsResponse,
    TrackingSystemStatus,
)

# Mounted under /admin/tracking by tracking_router.py.
router = APIRouter()


def _live_tracking_status() -> tuple[TrackingStatus, HeartbeatSnapshot, TrackingStatusSource]:
    """Resolve status from the separately supervised tracking service heartbeat."""
    heartbeat = read_heartbeat()
    if heartbeat.alive and heartbeat.status is not None:
        return heartbeat.status, heartbeat, "heartbeat"

    return unavailable_tracking_status(), heartbeat, "none"


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
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("30/minute")
def get_tracking_stats(
    request: Request,
    response: Response,
) -> TrackingStatsResponse:
    """Get tracking statistics (admin only)"""
    total_streamers = count_tracked_streamers_db()
    active_streamers = count_tracked_streamers_db(is_active=True)
    processing_enabled_streamers = count_tracked_streamers_db(processing_enabled=True)

    streamers_stats = {
        "total": total_streamers,
        "active": active_streamers,
        "processing_enabled": processing_enabled_streamers,
        "inactive": total_streamers - active_streamers,
    }

    jobs_stats = select_processing_stats_db()

    # Get system status — prefer the tracking process's Postgres heartbeat, since
    # monitoring runs in a separate container from the API (whose in-process
    # scheduler singleton is never started and would always read as 'down').
    tracking_status, heartbeat, source = _live_tracking_status()
    source_alive = source != "none"
    system_status = TrackingSystemStatus(
        monitoring_active=source_alive and tracking_status.stream_monitor.running,
        monitoring_degraded=tracking_status.stream_monitor.degraded,
        processing_queue_size=jobs_stats.get("pending", 0),
        failed_jobs=jobs_stats.get("failed", 0),
        scheduler_running=source_alive and tracking_status.scheduler.running,
        active_jobs=tracking_status.processing_queue.active_jobs,
        uptime_seconds=tracking_status.scheduler.uptime_seconds,
        heartbeat_state=heartbeat.state,
    )

    return TrackingStatsResponse(
        tracked_streamers=streamers_stats, processing_jobs=jobs_stats, system_status=system_status
    )


@router.get(
    "/service/status",
    response_model=TrackingServiceStatusResponse,
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
        429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit("60/minute")
def get_service_status(
    request: Request,
    response: Response,
) -> TrackingServiceStatusResponse:
    """Get tracking service status (admin only)"""
    # Reflect the real (possibly separate-container) tracking process via its
    # Postgres heartbeat, falling back to this process's scheduler.
    tracking_status, heartbeat, source = _live_tracking_status()
    return TrackingServiceStatusResponse.from_status(tracking_status, heartbeat, source)
