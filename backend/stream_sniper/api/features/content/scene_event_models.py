"""Contracts for the scene pulse and digest preview."""

from typing import Any

from pydantic import BaseModel


class SceneEvent(BaseModel):
    id: int
    event_type: str
    occurred_at: str
    creator_id: int | None = None
    creator_nick: str | None = None
    creator_display_name: str | None = None
    stream_id: int | None = None
    message_text_id: int | None = None
    title: str
    summary: str
    metadata: dict[str, Any]


class ScenePulse(BaseModel):
    items: list[SceneEvent]
    total: int
    days: int
    limit: int
    offset: int


class SceneDigest(BaseModel):
    days: int
    markdown: str
