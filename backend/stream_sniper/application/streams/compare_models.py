"""Contracts for the stream comparison lab."""

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
    start: str | None = None
    duration_seconds: int | None = None
    total_messages: int | None = None
    messages_per_minute: float | None = None
    unique_chatters: int | None = None
    new_chatters: int | None = None
    returning_chatters: int | None = None
    sub_share: float | None = None
    emote_share: float | None = None
    peak_messages: int | None = None
    peak_bucket_minute: str | None = None
    peak_viewers: int | None = None
    curve: list[CompareCurvePoint]


class PairRetention(BaseModel):
    from_stream_id: int
    to_stream_id: int
    from_audience: int
    to_audience: int
    retained: int
    retention_rate: float | None = None


class StreamComparison(BaseModel):
    streams: list[ComparedStream]
    retention: list[PairRetention]
