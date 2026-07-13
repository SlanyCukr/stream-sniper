"""Response/request contracts for the highlight-queue endpoints."""

from typing import Any, List, Optional

from pydantic import BaseModel, Field


class MomentQueueItem(BaseModel):
    """One enriched moment in the highlight queue, with its stream/creator context."""

    stream_id: int = Field(..., description="Stream ID", json_schema_extra={"example": 42})
    title: str = Field(..., description="Stream title")
    start: str = Field(..., description="Stream start timestamp (ISO 8601)")
    twitch_id: Optional[str] = Field(None, description="Twitch VOD ID for deep links")
    creator_id: Optional[int] = Field(None, description="Creator ID, if the stream has one")
    creator_display_name: Optional[str] = Field(None, description="Creator display name")
    bucket_minute: str = Field(..., description="Moment minute (ISO 8601)")
    offset_seconds: int = Field(..., description="Seconds from stream start (VOD jump target)")
    message_count: int = Field(..., description="Messages in the moment minute")
    baseline: float = Field(..., description="Trailing-window baseline used for detection")
    ratio: Optional[float] = Field(None, description="message_count / baseline; null when baseline is 0")
    unique_chatters: int = Field(..., description="Distinct chatters in the moment minute")
    sub_share: Optional[float] = Field(None, description="Subscriber message share (0-1); null if unknown")
    emote_share: Optional[float] = Field(None, description="Emote message share (0-1); null if unknown")
    top_phrases: Optional[List[Any]] = Field(None, description="Distinctive phrases for the moment")
    sample_messages: Optional[List[Any]] = Field(None, description="Representative repeated messages")
    status: str = Field(
        ..., description="Workflow status: pending, bookmarked, rejected, clipped, or published"
    )
    clip_url: Optional[str] = Field(None, description="Published Twitch/external clip URL")
    note: Optional[str] = Field(None, description="Curator note")


class MomentQueue(BaseModel):
    """A paginated page of the highlight queue."""

    items: List[MomentQueueItem] = Field(..., description="Moments on this page")
    total: int = Field(..., description="Total moments matching the filters")
    limit: int = Field(..., description="Page size")
    offset: int = Field(..., description="Page offset")


class MomentReviewRequest(BaseModel):
    """Body for setting a moment's review status."""

    status: str = Field(
        ...,
        pattern="^(bookmarked|rejected|clipped|published)$",
        description="Workflow status",
    )
    clip_url: Optional[str] = Field(None, pattern=r"^https?://", max_length=2000)
    note: Optional[str] = Field(None, max_length=500)


class MomentReviewResponse(BaseModel):
    """Result of a review mutation (null fields after a clear)."""

    status: Optional[str] = Field(None, description="New review status, or null after a clear")
    updated_at: Optional[str] = Field(None, description="When set (ISO 8601), or null after a clear")
    clip_url: Optional[str] = None
    note: Optional[str] = None
