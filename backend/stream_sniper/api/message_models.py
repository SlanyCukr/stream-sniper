"""Response contracts for the chronological stream message replay endpoint."""

from typing import List, Optional

from pydantic import BaseModel, Field


class MessageItem(BaseModel):
    """A single chat message in chronological replay order."""

    id: int = Field(..., description="Unique message ID", json_schema_extra={"example": 12345})
    time: str = Field(..., description="Message timestamp (ISO 8601)", json_schema_extra={"example": "2024-01-15T20:30:15"})
    chatter_id: int = Field(..., description="Chatter ID", json_schema_extra={"example": 42})
    nick: str = Field(..., description="Chatter nick", json_schema_extra={"example": "some_viewer"})
    text: str = Field(..., description="Message text", json_schema_extra={"example": "Hello everyone!"})
    is_subscriber: Optional[bool] = Field(
        None, description="Whether the chatter was a subscriber (null for legacy rows)"
    )
    badges: Optional[str] = Field(
        None,
        description="Sorted comma-joined name/version badge pairs (null for legacy rows)",
        json_schema_extra={"example": "moderator/1,subscriber/12"},
    )


class Cursor(BaseModel):
    """Keyset cursor identifying the last returned message."""

    after_ts: str = Field(..., description="Timestamp of the last returned message")
    after_id: int = Field(..., description="ID of the last returned message")


class MessagePage(BaseModel):
    """One page of chronological message replay."""

    messages: List[MessageItem] = Field(..., description="Messages in chronological order (oldest first)")
    next_cursor: Optional[Cursor] = Field(None, description="Cursor for the next page, or null on the last page")
    has_more: bool = Field(..., description="Whether more pages are available")
