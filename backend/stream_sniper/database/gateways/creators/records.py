"""Creator analytics persistence projections."""

from typing import NamedTuple


class CreatorRegularRow(NamedTuple):
    chatter_id: int
    nick: str
    streams_attended: int
    first_seen: str
    last_seen: str
    last_stream_attended: int
    message_count: int
