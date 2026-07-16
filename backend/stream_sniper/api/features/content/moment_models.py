"""Response/request contracts for the highlight-queue endpoints."""

from pydantic import AliasChoices, BaseModel, Field

from stream_sniper.database.gateways.content.records import (
    MomentReviewStatus,
    MomentStatus,
    SampleMessagePayload,
    TopPhrasePayload,
)


class MomentQueueItem(BaseModel):
    """One enriched moment in the highlight queue, with its stream/creator context."""

    stream_id: int = Field(..., description="Stream ID", json_schema_extra={"example": 42})
    title: str = Field(..., description="Stream title")
    start: str = Field(..., description="Stream start timestamp (ISO 8601)")
    twitch_vod_id: str | None = Field(
        None,
        validation_alias=AliasChoices("twitch_vod_id", "twitch_id"),
        serialization_alias="twitch_id",
        description="Twitch VOD ID for deep links",
    )
    creator_id: int | None = Field(None, description="Creator ID, if the stream has one")
    creator_display_name: str | None = Field(None, description="Creator display name")
    bucket_minute: str = Field(..., description="Moment minute (ISO 8601)")
    offset_seconds: int = Field(..., description="Seconds from stream start (VOD jump target)")
    message_count: int = Field(..., description="Messages in the moment minute")
    baseline: float = Field(..., description="Trailing-window baseline used for detection")
    ratio: float | None = Field(None, description="message_count / baseline; null when baseline is 0")
    unique_chatters: int = Field(..., description="Distinct chatters in the moment minute")
    sub_share: float | None = Field(None, description="Subscriber message share (0-1); null if unknown")
    emote_share: float | None = Field(None, description="Emote message share (0-1); null if unknown")
    top_phrases: list[TopPhrasePayload] | None = Field(None, description="Distinctive phrases for the moment")
    sample_messages: list[SampleMessagePayload] | None = Field(None, description="Representative repeated messages")
    status: MomentStatus = Field(
        ..., description="Workflow status: pending, bookmarked, rejected, clipped, or published"
    )
    clip_url: str | None = Field(None, description="Published Twitch/external clip URL")
    note: str | None = Field(None, description="Curator note")


class MomentQueue(BaseModel):
    """A paginated page of the highlight queue."""

    items: list[MomentQueueItem] = Field(..., description="Moments on this page")
    total: int = Field(..., description="Total moments matching the filters")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Page offset")


class MomentReviewRequest(BaseModel):
    """Body for setting a moment's review status."""

    status: MomentReviewStatus = Field(
        ...,
        pattern="^(bookmarked|rejected|clipped|published)$",
        description="Workflow status",
    )
    clip_url: str | None = Field(None, pattern=r"^https?://", max_length=2000)
    note: str | None = Field(None, max_length=500)


class MomentReviewResponse(BaseModel):
    """Result of a review mutation (null fields after a clear)."""

    status: MomentReviewStatus | None = Field(None, description="New review status, or null after a clear")
    updated_at: str | None = Field(None, description="When set (ISO 8601), or null after a clear")
    clip_url: str | None = None
    note: str | None = None
