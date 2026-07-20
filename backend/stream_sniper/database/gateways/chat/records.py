"""Named records produced by chat persistence gateways."""

from datetime import datetime
from typing import NamedTuple

from ...core.wire_format import to_char_wire_us


class MessageReplayRow(NamedTuple):
    id: int
    time: str
    chatter_id: int
    nick: str
    text: str
    is_subscriber: bool | None
    badges: str | None


# Shared replay projection — kept beside MessageReplayRow because the column
# order must match its field order (replay + export gateways both build from it).
REPLAY_COLUMNS = (
    f"m.id, {to_char_wire_us('m.time')}, m.chatter_id, c.nick, mt.text, "
    "m.is_subscriber, m.badges"
)
REPLAY_JOINS = "FROM message m\nJOIN chatter c ON c.id = m.chatter_id\nJOIN message_text mt ON mt.id = m.message_text_id"


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


class ChatterProfileRow(NamedTuple):
    id: int
    nick: str
    is_bot: bool | None
    bot_reason: str | None


class ChatterStreamActivityRow(NamedTuple):
    stream_id: int
    stream_title: str
    stream_start: datetime
    creator_id: int
    creator_display_name: str
    message_count: int
    is_bot: bool | None
