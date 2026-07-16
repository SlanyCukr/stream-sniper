"""Response contracts for core stream listing and detail endpoints."""

from pydantic import BaseModel, Field


class StreamListItem(BaseModel):
    stream_id: int
    creator_name: str
    start: str
    end: str | None
    thumbnail_url: str | None
    message_count: int


class StreamParticipant(BaseModel):
    chatter_id: int
    nick: str


class StreamInfo(BaseModel):
    title: str | None
    start: str
    end: str | None
    thumbnail_url: str | None
    message_count: int
    creator_nick: str
    creator_display_name: str
    profile_image_url: str | None
    creator_id: int


class RankedChatter(BaseModel):
    chatter_id: int
    nick: str
    count: int


class OtherCreator(BaseModel):
    creator_id: int
    nick: str


class StreamsResponse(BaseModel):
    """Paginated list of streams with a matching filtered row count."""

    streams: list[StreamListItem] = Field(..., description="Named stream listing entries")
    total: int = Field(..., description="Filtered row count used for pagination")
    offset: int = Field(..., description="Current zero-based row offset")
    limit: int = Field(..., description="Maximum rows returned by this page")


class StreamDetails(BaseModel):
    """Detailed analytics for one stream."""

    info: StreamInfo
    most_active_chatters: list[RankedChatter]
    most_tagged_chatters: list[RankedChatter]
    other_creators: list[OtherCreator]
    chatters: list[StreamParticipant]
