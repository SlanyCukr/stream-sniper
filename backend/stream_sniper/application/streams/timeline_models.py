"""Canonical stream-timeline read models shared with the API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import AliasChoices, BaseModel, Field

from stream_sniper.database.gateways.content.records import (
    MomentReviewStatus,
    SampleMessagePayload,
    TopPhrasePayload,
)

if TYPE_CHECKING:
    from stream_sniper.analytics.calculations.moments import DetectedMoment
    from stream_sniper.database.gateways.analytics.records import (
        StreamBucketRow,
        StreamMetricsRow,
    )
    from stream_sniper.database.gateways.content.records import StreamMomentRow
    from stream_sniper.database.gateways.streams.records import StreamContextChangeRow


class TimelineBucket(BaseModel):
    bucket_minute: str
    message_count: int
    unique_chatters: int
    sub_messages: int | None = None
    emote_messages: int | None = None

    @classmethod
    def from_row(cls, row: StreamBucketRow) -> TimelineBucket:
        return cls(
            bucket_minute=row.bucket_minute,
            message_count=row.message_count,
            unique_chatters=row.unique_chatters,
            sub_messages=row.sub_messages,
            emote_messages=row.emote_messages,
        )


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

    @classmethod
    def from_row(cls, row: StreamMomentRow) -> TimelineMoment:
        """Build a persisted timeline moment from a stored moment row."""
        return cls(
            bucket_minute=row.bucket_minute,
            offset_seconds=row.offset_seconds,
            message_count=row.message_count,
            baseline=row.baseline,
            ratio=row.ratio,
            unique_chatters=row.unique_chatters,
            sub_share=row.sub_share,
            emote_share=row.emote_share,
            top_phrases=row.top_phrases,
            sample_messages=row.sample_messages,
            status=row.status,
            persisted=True,
        )

    @classmethod
    def from_detected(cls, moment: DetectedMoment) -> TimelineMoment:
        """Build a non-persisted timeline moment from a live-detected spike."""
        return cls(
            bucket_minute=moment.bucket_minute,
            offset_seconds=moment.offset_seconds,
            message_count=moment.message_count,
            baseline=moment.baseline,
            ratio=moment.ratio,
            unique_chatters=moment.unique_chatters,
        )


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

    @classmethod
    def from_row(cls, row: StreamMetricsRow) -> TimelineMetrics:
        """Coalesce None counters to 0; leave sub/emote as None (unknown)."""
        return cls(
            total_messages=row.total_messages or 0,
            unique_chatters=row.unique_chatters or 0,
            duration_seconds=row.duration_seconds,
            messages_per_minute=row.messages_per_minute,
            peak_messages=row.peak_messages or 0,
            peak_bucket_minute=row.peak_bucket_minute,
            new_chatters=row.new_chatters or 0,
            returning_chatters=row.returning_chatters or 0,
            sub_messages=row.sub_messages,
            emote_messages=row.emote_messages,
        )


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

    @classmethod
    def from_row(cls, row: StreamContextChangeRow) -> StreamContextChange:
        return cls(
            t=row.sampled_at,
            title=row.title,
            category_id=row.category_id,
            category_name=row.category_name,
            language=row.language,
            tags=row.tags or [],
            is_mature=row.is_mature,
        )


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
