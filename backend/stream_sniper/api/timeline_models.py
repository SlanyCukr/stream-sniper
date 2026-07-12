"""Pydantic contracts for the per-stream timeline endpoint (snake_case wire format)."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class TimelineBucket(BaseModel):
    bucket_minute: str
    message_count: int
    unique_chatters: int
    # None on synthesized (zero-filled) minutes and on buckets not yet re-rolled under 0008;
    # a legitimate 0 means "rolled up, none observed" — never coalesce None to 0.
    sub_messages: Optional[int] = None
    emote_messages: Optional[int] = None


class TimelineMoment(BaseModel):
    bucket_minute: str
    offset_seconds: int
    message_count: int
    baseline: float
    ratio: Optional[float]
    unique_chatters: int
    # True for moments read from the persisted stream_moment table, False for the live
    # detect_moments fallback. The frontend reads this as `m.persisted` to badge enriched moments.
    persisted: bool = False
    # Enrichment fields present only on persisted (stream_moment) moments; None on the live
    # detect_moments fallback path. `status` comes from moment_review (None = unreviewed).
    status: Optional[str] = None
    sub_share: Optional[float] = None
    emote_share: Optional[float] = None
    top_phrases: Optional[List[Dict[str, Any]]] = None
    sample_messages: Optional[List[Dict[str, Any]]] = None


class TimelineMetrics(BaseModel):
    total_messages: int
    unique_chatters: int
    duration_seconds: Optional[int]
    messages_per_minute: Optional[float]
    peak_messages: int
    peak_bucket_minute: Optional[str]
    new_chatters: int
    returning_chatters: int
    # Null until the stream is re-rolled under 0008 (unknown != 0; do not coalesce).
    sub_messages: Optional[int] = None
    emote_messages: Optional[int] = None


class ViewerSample(BaseModel):
    t: str  # UTC-naive ISO timestamp, aligned to the bucket grid
    viewer_count: int


class StreamTimeline(BaseModel):
    stream_id: int
    stream_start: Optional[str]
    twitch_id: Optional[str]
    bucket_seconds: int = 60
    buckets: List[TimelineBucket]
    moments: List[TimelineMoment]
    metrics: Optional[TimelineMetrics]  # None when stream_metrics has no row (un-rolled-up)
    viewer_samples: List[ViewerSample] = []
    peak_viewers: Optional[int] = None  # None when no viewer samples exist
