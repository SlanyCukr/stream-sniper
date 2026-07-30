"""Application read models for scene-wide chat search."""

from pydantic import BaseModel, Field

from ..streams.message_models import MessageItem


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
    message_id: int
    time: str = Field(..., description="Message timestamp (ISO 8601)")
    text: str
    chatter: HitChatter
    stream: HitStream
    creator: HitCreator


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


class ContextResponse(BaseModel):
    stream: ContextStream
    messages: list[MessageItem]
    hit_index: int = Field(..., description="Index of the searched message within messages")
