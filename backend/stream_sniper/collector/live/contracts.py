"""Structural event contracts at the Twitch client to live-ingestion boundary."""

from datetime import datetime
from typing import Protocol


class LiveStream(Protocol):
    id: str | int
    started_at: datetime
    title: str
    thumbnail_url: str


class ChatRoom(Protocol):
    name: str


class ChatUser(Protocol):
    name: str
    subscriber: bool
    badges: object | None


class ChatMessage(Protocol):
    id: str | None
    room: ChatRoom | None
    user: ChatUser
    text: str
    emotes: object | None
    sent_timestamp: int | float
