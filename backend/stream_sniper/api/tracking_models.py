"""
Request/response contracts shared by the tracking administration routers.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class TrackedStreamerCreate(BaseModel):
    """Model for creating a new tracked streamer"""
    twitch_username: str = Field(..., description="Twitch username", min_length=3, max_length=50)
    notes: Optional[str] = Field(None, description="Optional notes", max_length=1000)
    is_active: bool = Field(True, description="Whether tracking is active")
    processing_enabled: bool = Field(True, description="Whether processing is enabled")

    @field_validator('twitch_username')
    @classmethod
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


class TwitchChannelResult(BaseModel):
    """A single Twitch channel search suggestion."""
    login: str = Field(..., description="Twitch login (username)")
    display_name: str = Field(..., description="Channel display name")
    profile_image_url: str = Field("", description="Profile thumbnail URL")
    is_live: bool = Field(False, description="Whether the channel is currently live")


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
