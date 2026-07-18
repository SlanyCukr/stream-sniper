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


class ChatterLoyaltyRow(NamedTuple):
    """One creator a chatter has chatted in, from the creator_chatter_stats rollup."""

    creator_id: int
    creator_nick: str
    creator_display_name: str
    message_count: int
    streams_attended: int
    first_seen: str | None
    last_seen: str | None
