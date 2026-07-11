"""Pydantic contracts for the per-stream timeline endpoint (snake_case wire format)."""

from typing import List, Optional

from pydantic import BaseModel


class TimelineBucket(BaseModel):
    bucket_minute: str
    message_count: int
    unique_chatters: int


class TimelineMoment(BaseModel):
    bucket_minute: str
    offset_seconds: int
    message_count: int
    baseline: float
    ratio: Optional[float]
    unique_chatters: int


class TimelineMetrics(BaseModel):
    total_messages: int
    unique_chatters: int
    duration_seconds: Optional[int]
    messages_per_minute: Optional[float]
    peak_messages: int
    peak_bucket_minute: Optional[str]
    new_chatters: int
    returning_chatters: int


class StreamTimeline(BaseModel):
    stream_id: int
    stream_start: Optional[str]
    twitch_id: Optional[str]
    bucket_seconds: int = 60
    buckets: List[TimelineBucket]
    moments: List[TimelineMoment]
    metrics: Optional[TimelineMetrics]  # None when stream_metrics has no row (un-rolled-up)
