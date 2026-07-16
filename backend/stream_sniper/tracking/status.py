"""Typed status values shared by the tracking process, heartbeat, and API."""

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class StreamObservation(StrEnum):
    LIVE = "live"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class SchedulerStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    running: bool
    start_time: str | None
    uptime_seconds: float | None
    monitor_interval: int = Field(ge=1)
    max_concurrent_jobs: int = Field(ge=1)
    max_retries: int = Field(ge=0)


class StreamMonitorStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    running: bool
    check_interval: int = Field(ge=1)
    tracked_streamers_count: int = Field(ge=0)
    last_stream_states: dict[str, StreamObservation]
    successful_checks: int = Field(default=0, ge=0)
    failed_checks: int = Field(default=0, ge=0)
    unknown_checks: int = Field(default=0, ge=0)
    degraded: bool = False
    last_cycle_completed_at: str | None = None
    last_successful_cycle: str | None = None


class ProcessingQueueStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    running: bool
    active_jobs: int = Field(ge=0)
    max_concurrent_jobs: int = Field(ge=1)
    max_retries: int = Field(ge=0)
    active_job_ids: list[int]


class TrackingStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    scheduler: SchedulerStatus
    stream_monitor: StreamMonitorStatus
    processing_queue: ProcessingQueueStatus


class HeartbeatState(StrEnum):
    FRESH = "fresh"
    STALE = "stale"
    MISSING = "missing"
    INCOMPATIBLE = "incompatible"


class HeartbeatSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: HeartbeatState
    status: TrackingStatus | None = None
    age_seconds: float | None = Field(default=None, ge=0)
    alive: bool = False
    validation_error: str | None = None


TrackingStatusSource = Literal["heartbeat", "none"]


def unavailable_tracking_status() -> TrackingStatus:
    """Return the explicit status used when no live tracking heartbeat exists."""
    return TrackingStatus(
        scheduler=SchedulerStatus(
            running=False,
            start_time=None,
            uptime_seconds=None,
            monitor_interval=300,
            max_concurrent_jobs=3,
            max_retries=3,
        ),
        stream_monitor=StreamMonitorStatus(
            running=False,
            check_interval=300,
            tracked_streamers_count=0,
            last_stream_states={},
        ),
        processing_queue=ProcessingQueueStatus(
            running=False,
            active_jobs=0,
            max_concurrent_jobs=3,
            max_retries=3,
            active_job_ids=[],
        ),
    )
