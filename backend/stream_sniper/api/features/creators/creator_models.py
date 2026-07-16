"""Named response contracts for creator catalog endpoints."""

from pydantic import BaseModel


class CreatorListItem(BaseModel):
    creator_id: int
    display_name: str


class CreatorTopChatter(BaseModel):
    chatter_id: int
    nick: str
    message_count: int
