"""Named records produced by chat persistence gateways."""

from datetime import datetime
from typing import NamedTuple


class MessageReplayRow(NamedTuple):
    id: int
    time: str
    chatter_id: int
    nick: str
    text: str
    is_subscriber: bool | None
    badges: str | None


class ChatterMessageRow(NamedTuple):
    stream_id: int
    stream_title: str
    creator_display_name: str
    text: str
    sent_at: str


class PhraseSourceRow(NamedTuple):
    text: str
    chatter_id: int
    occurrence_count: int


class MomentWindowRow(NamedTuple):
    sent_at: datetime
    text: str
    chatter_id: int
    is_subscriber: bool | None
    emote_count: int | None


class ChatterIdentityRow(NamedTuple):
    id: int
    is_bot: bool | None


class ChatterSearchRow(NamedTuple):
    chatter_id: int
    nick: str
    is_bot: bool | None


class ChatterStreamActivityRow(NamedTuple):
    stream_id: int
    stream_title: str
    stream_start: datetime
    creator_id: int
    creator_display_name: str
    message_count: int
    is_bot: bool | None
