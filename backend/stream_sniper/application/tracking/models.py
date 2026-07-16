"""Application-owned tracking records shared across adapters."""

from datetime import datetime
from typing import Literal, NamedTuple

JobStatus = Literal["pending", "in_progress", "completed", "failed"]
JOB_STATUS_PENDING: JobStatus = "pending"
JOB_STATUS_IN_PROGRESS: JobStatus = "in_progress"
JOB_STATUS_COMPLETED: JobStatus = "completed"
JOB_STATUS_FAILED: JobStatus = "failed"


class TrackedStreamer(NamedTuple):
    id: int
    creator_id: int
    twitch_username: str
    display_name: str
    is_active: bool
    last_stream_check: datetime | None
    last_processed_twitch_vod_id: int | None
    processing_enabled: bool
    created_at: datetime
    updated_at: datetime
    created_by: int
    notes: str | None
    creator_display_name: str
    profile_image_url: str | None
    created_by_username: str | None


class ProcessingJob(NamedTuple):
    id: int
    tracked_streamer_id: int
    twitch_vod_id: int
    status: JobStatus
    started_at: datetime | None
    completed_at: datetime | None
    error_message: str | None
    retry_count: int
    created_at: datetime
    updated_at: datetime
    twitch_username: str
    streamer_display_name: str
    stream_title: str | None
    stream_start: datetime | None
