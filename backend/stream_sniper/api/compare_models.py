"""Contracts for the stream comparison lab."""

from typing import List, Optional

from pydantic import BaseModel


class CompareCurvePoint(BaseModel):
    percent: int
    message_count: int
    unique_chatters: int


class ComparedStream(BaseModel):
    stream_id: int
    creator_id: int
    creator_nick: str
    creator_display_name: str
    title: str
    start: Optional[str] = None
    duration_seconds: Optional[int] = None
    total_messages: Optional[int] = None
    messages_per_minute: Optional[float] = None
    unique_chatters: Optional[int] = None
    new_chatters: Optional[int] = None
    returning_chatters: Optional[int] = None
    sub_share: Optional[float] = None
    emote_share: Optional[float] = None
    peak_messages: Optional[int] = None
    peak_bucket_minute: Optional[str] = None
    peak_viewers: Optional[int] = None
    curve: List[CompareCurvePoint]


class PairRetention(BaseModel):
    from_stream_id: int
    to_stream_id: int
    from_audience: int
    to_audience: int
    retained: int
    retention_rate: Optional[float] = None


class StreamComparison(BaseModel):
    streams: List[ComparedStream]
    retention: List[PairRetention]
