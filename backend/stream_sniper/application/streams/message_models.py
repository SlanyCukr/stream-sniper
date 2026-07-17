"""Canonical chronological-message read models shared with the API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from stream_sniper.database.gateways.chat.records import MessageReplayRow


class MessageItem(BaseModel):
    id: int = Field(..., description="Unique message ID")
    time: str = Field(..., description="Message timestamp (ISO 8601)")
    chatter_id: int
    nick: str
    text: str
    is_subscriber: bool | None = None
    badges: list[str]

    @classmethod
    def from_row(cls, row: MessageReplayRow) -> MessageItem:
        return cls(
            id=row.id,
            time=row.time,
            chatter_id=row.chatter_id,
            nick=row.nick,
            text=row.text,
            is_subscriber=row.is_subscriber,
            badges=row.badges.split(",") if row.badges else [],
        )


class Cursor(BaseModel):
    after_ts: str
    after_id: int


class MessagePage(BaseModel):
    messages: list[MessageItem]
    next_cursor: Cursor | None = None
    has_more: bool
