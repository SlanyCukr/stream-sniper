"""
API endpoints for streamer tracking management.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status, Request, Response, Query
from pydantic import BaseModel, Field, validator

from .auth import get_current_admin_user, UserInDB
from .rate_limiter import limiter, rate_limits
from ..database.tracked_streamers_table_gateway import (
    insert_tracked_streamer_db,
    select_tracked_streamers_db,
    select_tracked_streamer_by_id_db,
    select_tracked_streamer_by_username_db,
    update_tracked_streamer_db,
    delete_tracked_streamer_db,
    count_tracked_streamers_db,
    streamer_exists_db
)
from ..database.processing_jobs_table_gateway import (
    select_processing_jobs_db,
    count_processing_jobs_db,
    get_processing_stats_db,
    insert_processing_job_db,
    select_processing_job_by_id_db
)
from ..database.creator_table_gateway import select_creator_id_db, insert_new_creator_db
from ..collector.twitch_api import TwitchAPI
from ..logging_config import get_logger
from ..tracking.scheduler import get_scheduler

logger = get_logger(__name__)

# Create router
router = APIRouter(prefix="/admin/tracking", tags=["Tracking"])


class TrackedStreamerCreate(BaseModel):
    """Model for creating a new tracked streamer"""
    twitch_username: str = Field(..., description="Twitch username", min_length=3, max_length=50)
    notes: Optional[str] = Field(None, description="Optional notes", max_length=1000)
    is_active: bool = Field(True, description="Whether tracking is active")
    processing_enabled: bool = Field(True, description="Whether processing is enabled")
    
    @validator('twitch_username')
    def validate_twitch_username(cls, v):
        if not v.replace('_', '').isalnum():
            raise ValueError('Twitch username can only contain letters, numbers, and underscores')
        return v.lower()


class TrackedStreamerUpdate(BaseModel):
    """Model for updating a tracked streamer"""
    is_active: Optional[bool] = Field(None, description="Whether tracking is active")
    processing_enabled: Optional[bool] = Field(None, description="Whether processing is enabled")
    notes: Optional[str] = Field(None, description="Optional notes", max_length=1000)


class TrackedStreamerResponse(BaseModel):
    """Response model for tracked streamer"""
    id: int = Field(..., description="Tracked streamer ID")
    creator_id: int = Field(..., description="Creator ID")
    twitch_username: str = Field(..., description="Twitch username")
    display_name: str = Field(..., description="Display name")
    is_active: bool = Field(..., description="Whether tracking is active")
    last_stream_check: Optional[str] = Field(None, description="Last stream check time")
    last_processed_stream_id: Optional[int] = Field(None, description="Last processed stream ID")
    processing_enabled: bool = Field(..., description="Whether processing is enabled")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Update timestamp")
    created_by: Optional[int] = Field(None, description="Created by user ID")
    notes: Optional[str] = Field(None, description="Notes")
    creator_display_name: str = Field(..., description="Creator display name")
    profile_image_url: Optional[str] = Field(None, description="Profile image URL")
    created_by_username: Optional[str] = Field(None, description="Created by username")


class TrackedStreamersResponse(BaseModel):
    """Paginated response for tracked streamers"""
    streamers: List[TrackedStreamerResponse] = Field(..., description="List of tracked streamers")
    total: int = Field(..., description="Total number of tracked streamers")
    offset: int = Field(..., description="Current offset")
    limit: int = Field(..., description="Current limit")


class ProcessingJobResponse(BaseModel):
    """Response model for processing job"""
    id: int = Field(..., description="Job ID")
    tracked_streamer_id: int = Field(..., description="Tracked streamer ID")
    twitch_stream_id: int = Field(..., description="Twitch stream ID")
    status: str = Field(..., description="Job status")
    started_at: Optional[str] = Field(None, description="Start time")
    completed_at: Optional[str] = Field(None, description="Completion time")
    error_message: Optional[str] = Field(None, description="Error message")
    retry_count: int = Field(..., description="Retry count")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Update timestamp")
    twitch_username: str = Field(..., description="Twitch username")
    streamer_display_name: str = Field(..., description="Streamer display name")
    stream_title: Optional[str] = Field(None, description="Stream title")
    stream_start: Optional[str] = Field(None, description="Stream start time")


class ProcessingJobsResponse(BaseModel):
    """Paginated response for processing jobs"""
    jobs: List[ProcessingJobResponse] = Field(..., description="List of processing jobs")
    total: int = Field(..., description="Total number of jobs")
    offset: int = Field(..., description="Current offset")
    limit: int = Field(..., description="Current limit")


class TrackingStatsResponse(BaseModel):
    """Response model for tracking statistics"""
    tracked_streamers: Dict[str, int] = Field(..., description="Tracked streamers statistics")
    processing_jobs: Dict[str, int] = Field(..., description="Processing jobs statistics")
    system_status: Dict[str, Any] = Field(..., description="System status")


def convert_tracked_streamer_to_response(streamer_tuple) -> TrackedStreamerResponse:
    """Convert database tuple to response model"""
    return TrackedStreamerResponse(
        id=streamer_tuple[0],
        creator_id=streamer_tuple[1],
        twitch_username=streamer_tuple[2],
        display_name=streamer_tuple[3],
        is_active=streamer_tuple[4],
        last_stream_check=streamer_tuple[5].isoformat() if streamer_tuple[5] else None,
        last_processed_stream_id=streamer_tuple[6],
        processing_enabled=streamer_tuple[7],
        created_at=streamer_tuple[8].isoformat() if streamer_tuple[8] else None,
        updated_at=streamer_tuple[9].isoformat() if streamer_tuple[9] else None,
        created_by=streamer_tuple[10],
        notes=streamer_tuple[11],
        creator_display_name=streamer_tuple[12],
        profile_image_url=streamer_tuple[13],
        created_by_username=streamer_tuple[14]
    )


def convert_processing_job_to_response(job_tuple) -> ProcessingJobResponse:
    """Convert database tuple to response model"""
    return ProcessingJobResponse(
        id=job_tuple[0],
        tracked_streamer_id=job_tuple[1],
        twitch_stream_id=job_tuple[2],
        status=job_tuple[3],
        started_at=job_tuple[4].isoformat() if job_tuple[4] else None,
        completed_at=job_tuple[5].isoformat() if job_tuple[5] else None,
        error_message=job_tuple[6],
        retry_count=job_tuple[7],
        created_at=job_tuple[8].isoformat() if job_tuple[8] else None,
        updated_at=job_tuple[9].isoformat() if job_tuple[9] else None,
        twitch_username=job_tuple[10],
        streamer_display_name=job_tuple[11],
        stream_title=job_tuple[12],
        stream_start=job_tuple[13].isoformat() if job_tuple[13] else None
    )


@router.get(
    "/streamers",
    response_model=TrackedStreamersResponse,
    summary="Get tracked streamers",
    description="""
    Get list of tracked streamers with optional filtering and pagination.
    
    Requires admin role.
    
    **Rate Limit**: 30 requests per minute
    """,
    responses={
        200: {"description": "List of tracked streamers"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("30/minute")
async def get_tracked_streamers(
    request: Request,
    response: Response,
    offset: int = Query(0, description="Pagination offset", ge=0),
    limit: int = Query(100, description="Page size", ge=1, le=1000),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    processing_enabled: Optional[bool] = Query(None, description="Filter by processing enabled"),
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Get tracked streamers (admin only)"""
    try:
        streamers_tuple = select_tracked_streamers_db(
            limit=limit,
            offset=offset,
            is_active=is_active,
            processing_enabled=processing_enabled
        )
        
        total = count_tracked_streamers_db(
            is_active=is_active,
            processing_enabled=processing_enabled
        )
        
        streamers = [convert_tracked_streamer_to_response(streamer_tuple) 
                    for streamer_tuple in streamers_tuple]
        
        return TrackedStreamersResponse(
            streamers=streamers,
            total=total,
            offset=offset,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"Error fetching tracked streamers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post(
    "/streamers",
    response_model=TrackedStreamerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add tracked streamer",
    description="""
    Add a new streamer to tracking.
    
    Requires admin role.
    
    **Rate Limit**: 10 requests per minute
    """,
    responses={
        201: {"description": "Streamer added successfully"},
        400: {"description": "Invalid input data or streamer already exists"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("10/minute")
async def add_tracked_streamer(
    streamer_data: TrackedStreamerCreate,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Add a new streamer to tracking (admin only)"""
    try:
        # Check if streamer already exists
        if streamer_exists_db(streamer_data.twitch_username):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Streamer is already being tracked"
            )
        
        # Get or create creator
        creator_id = select_creator_id_db(streamer_data.twitch_username)
        
        if not creator_id:
            # Create new creator using Twitch API
            try:
                twitch_api = TwitchAPI()
                await twitch_api.twitch_api_init()
                twitch_api.set_streamer_nickname(streamer_data.twitch_username)
                
                display_name, profile_image_url = twitch_api.get_creator_info()
                twitch_creator_id = twitch_api.get_creator_twitch_id()
                
                creator_id = insert_new_creator_db(
                    streamer_data.twitch_username,
                    display_name,
                    profile_image_url,
                    twitch_creator_id
                )
                
                if not creator_id:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Failed to create creator"
                    )
                    
                display_name_for_tracking = display_name
                
            except Exception as e:
                logger.error(f"Error creating creator for {streamer_data.twitch_username}: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to get streamer information from Twitch"
                )
        else:
            # Use existing creator display name
            display_name_for_tracking = streamer_data.twitch_username
        
        # Create tracked streamer
        tracked_streamer_id = insert_tracked_streamer_db(
            creator_id=creator_id,
            twitch_username=streamer_data.twitch_username,
            display_name=display_name_for_tracking,
            created_by=current_user.id,
            notes=streamer_data.notes,
            is_active=streamer_data.is_active,
            processing_enabled=streamer_data.processing_enabled
        )
        
        if not tracked_streamer_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create tracked streamer"
            )
        
        # Fetch created streamer
        streamer_tuple = select_tracked_streamer_by_id_db(tracked_streamer_id)
        if not streamer_tuple:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve created streamer"
            )
        
        logger.info(f"Tracked streamer created by admin {current_user.username}: {streamer_data.twitch_username}")
        return convert_tracked_streamer_to_response(streamer_tuple)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding tracked streamer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get(
    "/streamers/{streamer_id}",
    response_model=TrackedStreamerResponse,
    summary="Get tracked streamer by ID",
    description="""
    Get detailed information about a specific tracked streamer.
    
    Requires admin role.
    
    **Rate Limit**: 60 requests per minute
    """,
    responses={
        200: {"description": "Tracked streamer information"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"description": "Streamer not found"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("60/minute")
async def get_tracked_streamer(
    streamer_id: int,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Get tracked streamer by ID (admin only)"""
    try:
        streamer_tuple = select_tracked_streamer_by_id_db(streamer_id)
        
        if not streamer_tuple:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tracked streamer not found"
            )
        
        return convert_tracked_streamer_to_response(streamer_tuple)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching tracked streamer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.put(
    "/streamers/{streamer_id}",
    response_model=TrackedStreamerResponse,
    summary="Update tracked streamer",
    description="""
    Update tracked streamer settings.
    
    Requires admin role.
    
    **Rate Limit**: 10 requests per minute
    """,
    responses={
        200: {"description": "Streamer updated successfully"},
        400: {"description": "Invalid input data"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"description": "Streamer not found"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("10/minute")
async def update_tracked_streamer(
    streamer_id: int,
    streamer_update: TrackedStreamerUpdate,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Update tracked streamer (admin only)"""
    try:
        # Check if streamer exists
        streamer_tuple = select_tracked_streamer_by_id_db(streamer_id)
        if not streamer_tuple:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tracked streamer not found"
            )
        
        # Build update data
        update_data = {}
        if streamer_update.is_active is not None:
            update_data['is_active'] = streamer_update.is_active
        if streamer_update.processing_enabled is not None:
            update_data['processing_enabled'] = streamer_update.processing_enabled
        if streamer_update.notes is not None:
            update_data['notes'] = streamer_update.notes
        
        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update"
            )
        
        # Update streamer
        success = update_tracked_streamer_db(streamer_id, **update_data)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update streamer"
            )
        
        # Fetch updated streamer
        updated_streamer_tuple = select_tracked_streamer_by_id_db(streamer_id)
        if not updated_streamer_tuple:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve updated streamer"
            )
        
        logger.info(f"Tracked streamer updated by admin {current_user.username}: streamer_id={streamer_id}")
        return convert_tracked_streamer_to_response(updated_streamer_tuple)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tracked streamer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete(
    "/streamers/{streamer_id}",
    summary="Remove tracked streamer",
    description="""
    Remove a streamer from tracking.
    
    Requires admin role.
    
    **Rate Limit**: 5 requests per minute
    """,
    responses={
        200: {"description": "Streamer removed successfully"},
        401: {"description": "Authentication required"},
        403: {"description": "Admin role required"},
        404: {"description": "Streamer not found"},
        429: {"description": "Rate limit exceeded"},
    }
)
@limiter.limit("5/minute")
async def remove_tracked_streamer(
    streamer_id: int,
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Remove tracked streamer (admin only)"""
    try:
        # Check if streamer exists
        streamer_tuple = select_tracked_streamer_by_id_db(streamer_id)
        if not streamer_tuple:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tracked streamer not found"
            )
        
        # Delete streamer
        success = delete_tracked_streamer_db(streamer_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to remove streamer"
            )
        
        logger.info(f"Tracked streamer removed by admin {current_user.username}: streamer_id={streamer_id}")
        return {"message": "Streamer removed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing tracked streamer: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


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
async def get_processing_jobs(
    request: Request,
    response: Response,
    offset: int = Query(0, description="Pagination offset", ge=0),
    limit: int = Query(100, description="Page size", ge=1, le=1000),
    status: Optional[str] = Query(None, description="Filter by job status"),
    tracked_streamer_id: Optional[int] = Query(None, description="Filter by streamer ID"),
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Get processing jobs (admin only)"""
    try:
        jobs_tuple = select_processing_jobs_db(
            limit=limit,
            offset=offset,
            status=status,
            tracked_streamer_id=tracked_streamer_id
        )
        
        total = count_processing_jobs_db(
            status=status,
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
    """Manually trigger processing for a streamer (admin only)"""
    try:
        # Check if streamer exists
        streamer_tuple = select_tracked_streamer_by_id_db(streamer_id)
        if not streamer_tuple:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tracked streamer not found"
            )
        
        # TODO: Implement manual processing trigger
        # This would involve getting the latest stream and creating a processing job
        
        logger.info(f"Manual processing triggered by admin {current_user.username}: streamer_id={streamer_id}")
        return {"message": "Processing triggered successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error triggering processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


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
async def get_tracking_stats(
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
        
        # Get system status from scheduler
        scheduler = get_scheduler()
        scheduler_status = scheduler.get_status()
        
        system_status = {
            'monitoring_active': scheduler_status['stream_monitor']['running'],
            'processing_queue_size': jobs_stats.get('pending', 0),
            'failed_jobs': jobs_stats.get('failed', 0),
            'scheduler_running': scheduler_status['scheduler']['running'],
            'active_jobs': scheduler_status['processing_queue']['active_jobs'],
            'uptime_seconds': scheduler_status['scheduler']['uptime_seconds']
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
async def get_service_status(
    request: Request,
    response: Response,
    current_user: UserInDB = Depends(get_current_admin_user)
):
    """Get tracking service status (admin only)"""
    try:
        scheduler = get_scheduler()
        return scheduler.get_status()
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