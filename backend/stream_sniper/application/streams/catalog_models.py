"""Response contracts for core stream listing and detail endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from stream_sniper.database.gateways.streams.records import (
        OtherCreatorRow,
        RankedChatterRow,
        StreamComprehensiveRow,
        StreamListRow,
        StreamParticipantRow,
    )


class StreamListItem(BaseModel):
    stream_id: int
    creator_name: str
    start: str
    end: str | None
    thumbnail_url: str | None
    message_count: int

    @classmethod
    def from_row(cls, row: StreamListRow) -> StreamListItem:
        return cls(
            stream_id=row.stream_id,
            creator_name=row.creator_name,
            start=row.start,
            end=row.end,
            thumbnail_url=row.thumbnail_url,
            message_count=row.message_count,
        )


class StreamParticipant(BaseModel):
    chatter_id: int
    nick: str

    @classmethod
    def from_row(cls, row: StreamParticipantRow) -> StreamParticipant:
        return cls(chatter_id=row.chatter_id, nick=row.nick)


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

    @classmethod
    def from_row(cls, row: StreamComprehensiveRow) -> StreamInfo:
        return cls(
            title=row.title,
            start=str(row.start),
            end=str(row.end) if row.end is not None else None,
            thumbnail_url=row.thumbnail_url,
            message_count=row.message_count,
            creator_nick=row.creator_nick,
            creator_display_name=row.creator_display_name,
            profile_image_url=row.profile_image_url,
            creator_id=row.creator_id,
        )


class RankedChatter(BaseModel):
    chatter_id: int
    nick: str
    count: int

    @classmethod
    def from_row(cls, row: RankedChatterRow) -> RankedChatter:
        return cls(chatter_id=row.chatter_id, nick=row.nick, count=row.rank_count)


class OtherCreator(BaseModel):
    creator_id: int
    nick: str

    @classmethod
    def from_row(cls, row: OtherCreatorRow) -> OtherCreator:
        return cls(creator_id=row.creator_id, nick=row.nick)


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
