"""Contracts for the scene pulse and digest preview."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SceneEvent(BaseModel):
    id: int
    event_type: str
    occurred_at: str
    creator_id: Optional[int] = None
    creator_nick: Optional[str] = None
    creator_display_name: Optional[str] = None
    stream_id: Optional[int] = None
    message_text_id: Optional[int] = None
    title: str
    summary: str
    metadata: Dict[str, Any]


class ScenePulse(BaseModel):
    items: List[SceneEvent]
    total: int
    days: int
    limit: int
    offset: int


class SceneDigest(BaseModel):
    days: int
    markdown: str
