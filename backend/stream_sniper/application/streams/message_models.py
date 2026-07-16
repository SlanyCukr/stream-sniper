"""Canonical chronological-message read models shared with the API."""

from pydantic import BaseModel, Field


class MessageItem(BaseModel):
    id: int = Field(..., description="Unique message ID")
    time: str = Field(..., description="Message timestamp (ISO 8601)")
    chatter_id: int
    nick: str
    text: str
    is_subscriber: bool | None = None
    badges: list[str]


class Cursor(BaseModel):
    after_ts: str
    after_id: int


class MessagePage(BaseModel):
    messages: list[MessageItem]
    next_cursor: Cursor | None = None
    has_more: bool
