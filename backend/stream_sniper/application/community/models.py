"""Canonical community-overlap read models shared with the API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from stream_sniper.database.gateways.community.records import (
        CommunityCreatorRow,
        CreatorNeighborRow,
    )


class OverlapCreator(BaseModel):
    creator_id: int
    nick: str
    display_name: str
    chatters: int
    regulars: int

    @classmethod
    def from_row(cls, row: CommunityCreatorRow) -> OverlapCreator:
        return cls(
            creator_id=row.creator_id,
            nick=row.nick,
            display_name=row.display_name,
            chatters=row.chatters,
            regulars=row.regulars,
        )


class OverlapPair(BaseModel):
    a: int
    b: int
    shared_chatters: int
    shared_regulars: int
    jaccard_chatters: float | None = None
    jaccard_regulars: float | None = None


class CommunityOverlap(BaseModel):
    creators: list[OverlapCreator]
    pairs: list[OverlapPair]
    computed_at: str | None = None


class CreatorNeighbor(BaseModel):
    creator_id: int
    nick: str
    display_name: str
    shared_chatters: int
    shared_regulars: int

    @classmethod
    def from_row(cls, row: CreatorNeighborRow) -> CreatorNeighbor:
        return cls(
            creator_id=row.creator_id,
            nick=row.nick,
            display_name=row.display_name,
            shared_chatters=row.shared_chatters,
            shared_regulars=row.shared_regulars,
        )


class CreatorNeighbors(BaseModel):
    creator_id: int
    metric: str
    neighbors: list[CreatorNeighbor]


class HeadToHeadCreator(BaseModel):
    """One side of a creator head-to-head: audience denominators + share of overlap."""

    creator_id: int
    nick: str
    display_name: str
    chatters: int
    regulars: int
    shared_chatter_share: float | None = None
    shared_regular_share: float | None = None


class CreatorHeadToHead(BaseModel):
    """Pairwise audience comparison. nullable=unknown: shares are null for empty audiences."""

    a: HeadToHeadCreator
    b: HeadToHeadCreator
    shared_chatters: int
    shared_regulars: int
    jaccard_chatters: float | None = None
    jaccard_regulars: float | None = None
    computed_at: str | None = None
