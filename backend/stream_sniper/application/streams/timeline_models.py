"""Canonical stream-timeline read models shared with the API."""

from pydantic import AliasChoices, BaseModel, Field

from stream_sniper.database.gateways.content.records import (
    MomentReviewStatus,
    SampleMessagePayload,
    TopPhrasePayload,
)


class TimelineBucket(BaseModel):
    bucket_minute: str
    message_count: int
    unique_chatters: int
    sub_messages: int | None = None
    emote_messages: int | None = None


class TimelineMoment(BaseModel):
    bucket_minute: str
    offset_seconds: int
    message_count: int
    baseline: float
    ratio: float | None
    unique_chatters: int
    persisted: bool = False
    status: MomentReviewStatus | None = None
    sub_share: float | None = None
    emote_share: float | None = None
    top_phrases: list[TopPhrasePayload] | None = None
    sample_messages: list[SampleMessagePayload] | None = None


class TimelineMetrics(BaseModel):
    total_messages: int
    unique_chatters: int
    duration_seconds: int | None
    messages_per_minute: float | None
    peak_messages: int
    peak_bucket_minute: str | None
    new_chatters: int
    returning_chatters: int
    sub_messages: int | None = None
    emote_messages: int | None = None


class ViewerSample(BaseModel):
    t: str
    viewer_count: int


class StreamContextChange(BaseModel):
    t: str
    title: str | None = None
    category_id: str | None = None
    category_name: str | None = None
    language: str | None = None
    tags: list[str] = Field(default_factory=list)
    is_mature: bool | None = None


class StreamTimeline(BaseModel):
    stream_id: int
    stream_start: str | None
    twitch_vod_id: str | None = Field(
        validation_alias=AliasChoices("twitch_vod_id", "twitch_id"),
        serialization_alias="twitch_id",
    )
    buckets: list[TimelineBucket]
    moments: list[TimelineMoment]
    metrics: TimelineMetrics | None
    bucket_seconds: int = 60
    viewer_samples: list[ViewerSample] = Field(default_factory=list)
    peak_viewers: int | None = None
    context_changes: list[StreamContextChange] = Field(default_factory=list)
