"""
Request/response contracts shared by the tracking administration routers.
"""

from typing import Literal, Self

from pydantic import BaseModel, Field, field_validator
from pydantic.json_schema import SkipJsonSchema

from stream_sniper.application.tracking.models import (
    JobStatus,
    ProcessingJob,
    TrackedStreamer,
)
from stream_sniper.database.gateways.streams.records import CreatorStreamSummaryRow

from ....tracking.status import (
    HeartbeatSnapshot,
    ProcessingQueueStatus,
    SchedulerStatus,
    StreamMonitorStatus,
    TrackingStatus,
    TrackingStatusSource,
)


class TrackedStreamerCreate(BaseModel):
    twitch_username: str = Field(..., min_length=3, max_length=50)
    notes: str | None = Field(None, max_length=1000)
    is_active: bool = True
    processing_enabled: bool = True

    @field_validator("twitch_username")
    @classmethod
    def validate_twitch_username(cls, v: str) -> str:
        if not v.replace("_", "").isalnum():
            raise ValueError("Twitch username can only contain letters, numbers, and underscores")
        return v.lower()


class TrackedStreamerUpdate(BaseModel):
    is_active: bool | SkipJsonSchema[None] = None
    processing_enabled: bool | SkipJsonSchema[None] = None
    notes: str | None = Field(None, max_length=1000)

    @field_validator("is_active", "processing_enabled", mode="before")
    @classmethod
    def reject_null_flags(cls, value: object) -> object:
        if value is None:
            raise ValueError("is_active and processing_enabled must be true or false")
        return value


class TrackedStreamerResponse(BaseModel):
    id: int
    creator_id: int
    twitch_username: str
    display_name: str
    is_active: bool
    last_stream_check: str | None = None
    last_processed_twitch_vod_id: int | None = Field(None, serialization_alias="last_processed_vod_id")
    processing_enabled: bool
    created_at: str
    updated_at: str
    created_by: int | None = None
    notes: str | None = None
    creator_display_name: str
    profile_image_url: str | None = None
    created_by_username: str | None = None
    # Collection summary (populated on list/detail reads; None until attached).
    # Lets the admin UI distinguish dormant channels (old/absent last stream)
    # from broken ingestion (active on Twitch but nothing collected).
    total_streams_collected: int | None = None
    last_collected_stream_start: str | None = None


class TrackedStreamersResponse(BaseModel):
    streamers: list[TrackedStreamerResponse]
    total: int
    offset: int
    limit: int


class ProcessingJobResponse(BaseModel):
    id: int
    tracked_streamer_id: int
    twitch_vod_id: int
    status: JobStatus
    started_at: str | None = None
    completed_at: str | None = None
    error_message: str | None = None
    retry_count: int
    created_at: str
    updated_at: str
    twitch_username: str
    streamer_display_name: str
    stream_title: str | None = None
    stream_start: str | None = None


class ProcessingJobsResponse(BaseModel):
    jobs: list[ProcessingJobResponse]
    total: int
    offset: int
    limit: int


class ProcessingTriggerResponse(BaseModel):
    """Outcome of requesting the next uncollected VOD for a streamer."""

    outcome: Literal["queued", "already_queued", "no_vod"]
    message: str
    queued: bool
    job_id: int | None = None
    twitch_vod_id: int | None = None
    vod_title: str | None = None


class TwitchProbeResponse(BaseModel):
    """On-demand Twitch snapshot for a tracked streamer — dormant vs broken triage."""

    is_live: bool
    archive_vod_count: int
    last_vod_created_at: str | None = None
    checked_at: str


class TrackingSystemStatus(BaseModel):
    """Flattened dashboard summary derived from a validated tracking snapshot."""

    monitoring_active: bool
    monitoring_degraded: bool
    processing_queue_size: int
    failed_jobs: int
    scheduler_running: bool
    active_jobs: int
    uptime_seconds: float | None
    heartbeat_state: str


class TrackingStatsResponse(BaseModel):
    tracked_streamers: dict[str, int]
    processing_jobs: dict[str, int]
    system_status: TrackingSystemStatus


class TrackingServiceStatusResponse(BaseModel):
    """Detailed tracking telemetry plus heartbeat provenance."""

    scheduler: SchedulerStatus
    stream_monitor: StreamMonitorStatus
    processing_queue: ProcessingQueueStatus
    heartbeat: HeartbeatSnapshot
    source: TrackingStatusSource

    @classmethod
    def from_status(
        cls,
        status: TrackingStatus,
        heartbeat: HeartbeatSnapshot,
        source: TrackingStatusSource,
    ) -> Self:
        return cls(
            scheduler=status.scheduler,
            stream_monitor=status.stream_monitor,
            processing_queue=status.processing_queue,
            heartbeat=heartbeat,
            source=source,
        )


class TwitchChannelResult(BaseModel):
    """A single Twitch channel search suggestion."""

    login: str
    display_name: str
    profile_image_url: str = ""
    is_live: bool = False


def convert_tracked_streamer_to_response(
    row: TrackedStreamer,
    summary: CreatorStreamSummaryRow | None = None,
) -> TrackedStreamerResponse:
    """Convert a gateway record to the transport model.

    ``summary`` (batched per-creator collection stats) is attached on list and
    detail reads; mutation responses skip it — the admin UI re-reads the list.
    """
    return TrackedStreamerResponse(
        id=row.id,
        creator_id=row.creator_id,
        twitch_username=row.twitch_username,
        display_name=row.display_name,
        is_active=row.is_active,
        last_stream_check=row.last_stream_check.isoformat() if row.last_stream_check else None,
        last_processed_twitch_vod_id=row.last_processed_twitch_vod_id,
        processing_enabled=row.processing_enabled,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
        created_by=row.created_by,
        notes=row.notes,
        creator_display_name=row.creator_display_name,
        profile_image_url=row.profile_image_url,
        created_by_username=row.created_by_username,
        total_streams_collected=summary.total_streams if summary else None,
        last_collected_stream_start=(
            summary.last_stream_start.isoformat() if summary and summary.last_stream_start else None
        ),
    )


def convert_processing_job_to_response(
    row: ProcessingJob,
) -> ProcessingJobResponse:
    """Convert a gateway record to the transport model."""
    return ProcessingJobResponse(
        id=row.id,
        tracked_streamer_id=row.tracked_streamer_id,
        twitch_vod_id=row.twitch_vod_id,
        status=row.status,
        started_at=row.started_at.isoformat() if row.started_at else None,
        completed_at=row.completed_at.isoformat() if row.completed_at else None,
        error_message=row.error_message,
        retry_count=row.retry_count,
        created_at=row.created_at.isoformat(),
        updated_at=row.updated_at.isoformat(),
        twitch_username=row.twitch_username,
        streamer_display_name=row.streamer_display_name,
        stream_title=row.stream_title,
        stream_start=row.stream_start.isoformat() if row.stream_start else None,
    )
