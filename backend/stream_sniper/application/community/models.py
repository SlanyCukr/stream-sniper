"""Canonical community-overlap read models shared with the API."""

from pydantic import BaseModel


class OverlapCreator(BaseModel):
    creator_id: int
    nick: str
    display_name: str
    chatters: int
    regulars: int


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


class CreatorNeighbors(BaseModel):
    creator_id: int
    metric: str
    neighbors: list[CreatorNeighbor]
