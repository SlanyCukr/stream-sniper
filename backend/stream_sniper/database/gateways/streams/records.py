"""Records owned by stream persistence."""

from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple


class StreamComprehensiveRow(NamedTuple):
    title: str | None
    start: str | datetime
    end: str | datetime | None
    thumbnail_url: str | None
    message_count: int
    creator_nick: str
    creator_display_name: str
    profile_image_url: str | None
    creator_id: int


class ViewerSampleRow(NamedTuple):
    sampled_at: str
    viewer_count: int


class StreamContextChangeRow(NamedTuple):
    sampled_at: str
    title: str | None
    category_id: str | None
    category_name: str | None
    language: str | None
    tags: list[str] | None
    is_mature: bool | None


class LiveNowRow(NamedTuple):
    creator_id: int
    nick: str
    display_name: str
    profile_image_url: str | None
    viewer_count: int
    title: str | None
    session_started_at: str | None
    sampled_at: str


class MentionedChatterRow(NamedTuple):
    chatter_id: int
    nick: str
    mention_count: int


class MentionPairRow(NamedTuple):
    from_chatter_id: int
    from_nick: str
    to_chatter_id: int
    to_nick: str
    pair_count: int


class ChatterMessageTextRow(NamedTuple):
    text: str


class StreamListRow(NamedTuple):
    stream_id: int
    creator_name: str
    start: str
    end: str | None
    thumbnail_url: str | None
    message_count: int


class RankedChatterRow(NamedTuple):
    chatter_id: int
    nick: str
    rank_count: int


class OtherCreatorRow(NamedTuple):
    creator_id: int
    nick: str


class StreamParticipantRow(NamedTuple):
    chatter_id: int
    nick: str


@dataclass(frozen=True)
class StreamContextSample:
    tracked_streamer_id: int
    twitch_stream_session_id: int | str
    sampled_at: datetime
    session_started_at: datetime | None
    title: str | None
    category_id: str | None
    category_name: str | None
    language: str | None
    tags: list[str] | None
    is_mature: bool | None
