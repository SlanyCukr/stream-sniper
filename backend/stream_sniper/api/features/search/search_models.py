"""Response contracts for scene-wide chat search endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

from ....application.streams.message_models import MessageItem
from ....database.gateways.chat.message_replay_gateway import StreamContextRow
from ....database.gateways.chat.message_search_gateway import SearchHitRow


class HitChatter(BaseModel):
    id: int
    nick: str
    is_bot: bool | None = Field(None, description="Bot classification (null = not yet classified)")


class HitStream(BaseModel):
    id: int
    title: str


class HitCreator(BaseModel):
    id: int
    nick: str
    display_name: str


class SearchHit(BaseModel):
    """One matched message with its chatter / stream / creator context."""

    message_id: int
    time: str = Field(..., description="Message timestamp (ISO 8601)")
    text: str
    chatter: HitChatter
    stream: HitStream
    creator: HitCreator

    @classmethod
    def from_row(cls, row: SearchHitRow) -> SearchHit:
        return cls(
            message_id=row.message_id,
            time=row.time,
            text=row.text,
            chatter=HitChatter(id=row.chatter_id, nick=row.chatter_nick, is_bot=row.chatter_is_bot),
            stream=HitStream(id=row.stream_id, title=row.stream_title),
            creator=HitCreator(id=row.creator_id, nick=row.creator_nick, display_name=row.creator_display_name),
        )


class SearchMessagesResponse(BaseModel):
    query: str
    items: list[SearchHit]
    has_more: bool


class FirstMatchResponse(BaseModel):
    query: str
    first: SearchHit | None = None
    by_creator: list[SearchHit]
    total_matches: int = Field(..., description="Total matching messages (exact up to the internal text-id cap)")


class FrequencyPoint(BaseModel):
    date: str = Field(..., description="Calendar day (YYYY-MM-DD)")
    count: int


class FrequencyResponse(BaseModel):
    query: str
    days: int
    points: list[FrequencyPoint] = Field(..., description="Zero-filled continuous daily counts, oldest first")


class ContextCreator(BaseModel):
    id: int
    nick: str
    display_name: str


class ContextStream(BaseModel):
    id: int
    title: str
    creator: ContextCreator

    @classmethod
    def from_row(cls, row: StreamContextRow) -> ContextStream:
        return cls(
            id=row.stream_id,
            title=row.stream_title,
            creator=ContextCreator(id=row.creator_id, nick=row.creator_nick, display_name=row.creator_display_name),
        )


class ContextResponse(BaseModel):
    stream: ContextStream
    messages: list[MessageItem]
    hit_index: int = Field(..., description="Index of the searched message within messages")
