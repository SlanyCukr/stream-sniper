"""Records owned by identity persistence."""

from datetime import datetime
from typing import NamedTuple

from ....identity import UserRole


class CreatorSummaryRow(NamedTuple):
    creator_id: int
    nick: str
    display_name: str
    profile_image_url: str | None
    twitch_user_id: int | None
    total_streams: int
    first_stream_at: str | None
    last_stream_at: str | None
    total_messages: int
    duration_seconds: int | None
    messages_per_minute: float | None
    audience_size: int
    regulars: int
    latest_stream_id: int | None
    latest_stream_title: str | None
    latest_stream_start: str | None


class CreatorListRow(NamedTuple):
    creator_id: int
    display_name: str


class CreatorTopChatterRow(NamedTuple):
    chatter_id: int
    nick: str
    message_count: int


class UserRow(NamedTuple):
    id: int
    username: str
    email: str
    password_hash: str
    role: UserRole
    is_active: bool
    created_at: datetime


class PublicUserRow(NamedTuple):
    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserSystemStatsRow(NamedTuple):
    total_users: int
    active_users: int
    admin_users: int
    recent_registrations: int
