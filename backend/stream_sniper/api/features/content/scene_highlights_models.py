"""Response contracts for the public scene-wide Highlights Wall.

`top_phrases` / `sample_messages` mirror the highlight-queue (moment) endpoint's shapes
exactly (`TopPhrasePayload` / `SampleMessagePayload`) so the frontend can reuse its moment
rendering for scene highlights. `ratio` / `sub_share` / `emote_share` stay nullable
(nullable = unknown; a NULL is never coalesced to 0).
"""

from pydantic import BaseModel, Field

from ....database.gateways.content.records import SampleMessagePayload, TopPhrasePayload


class Highlight(BaseModel):
    """One scene-wide hype-ranked moment with its stream, creator, and curation context."""

    stream_id: int = Field(..., description="Stream ID", json_schema_extra={"example": 42})
    stream_title: str = Field(..., description="Stream title")
    twitch_id: str | None = Field(None, description="Twitch VOD ID for deep links (bigint as string)")
    creator_id: int = Field(..., description="Creator ID")
    creator_nick: str = Field(..., description="Creator login/nick")
    creator_display_name: str = Field(..., description="Creator display name")
    bucket_minute: str = Field(..., description="Moment minute (ISO 8601)")
    offset_seconds: int = Field(..., description="Seconds from stream start (VOD jump target)")
    ratio: float | None = Field(None, description="message_count / baseline; null when baseline is 0")
    message_count: int = Field(..., description="Messages in the moment minute")
    unique_chatters: int = Field(..., description="Distinct chatters in the moment minute")
    sub_share: float | None = Field(None, description="Subscriber message share (0-1); null if unknown")
    emote_share: float | None = Field(None, description="Emote message share (0-1); null if unknown")
    top_phrases: list[TopPhrasePayload] | None = Field(None, description="Distinctive phrases for the moment")
    sample_messages: list[SampleMessagePayload] | None = Field(None, description="Representative repeated messages")
    clip_url: str | None = Field(None, description="Published Twitch/external clip URL")
    review_status: str | None = Field(
        None, description="Curation status (bookmarked/clipped/published); null when not reviewed"
    )


class HighlightsResponse(BaseModel):
    """A page of the scene-wide Highlights Wall."""

    window: str = Field(..., description="Applied window: all, 7, or 30")
    sort: str = Field(..., description="Applied ordering: hype or recent")
    items: list[Highlight] = Field(..., description="Highlights on this page")
    has_more: bool = Field(..., description="True when a further page exists")
