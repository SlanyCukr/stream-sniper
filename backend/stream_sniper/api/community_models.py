"""Response contracts for community-overlap endpoints."""

from typing import List, Optional

from pydantic import BaseModel, Field


class OverlapCreator(BaseModel):
    """A creator in the overlap set, with audience-size denominators."""

    creator_id: int = Field(..., description="Creator ID", json_schema_extra={"example": 5})
    nick: str = Field(..., description="Creator login/nick")
    display_name: str = Field(..., description="Creator display name")
    chatters: int = Field(..., description="Distinct chatters in this creator's audience")
    regulars: int = Field(..., description="Chatters with streams_attended >= 3")


class OverlapPair(BaseModel):
    """Shared-audience overlap between two creators (creator_a < creator_b)."""

    a: int = Field(..., description="Creator A ID (lower)")
    b: int = Field(..., description="Creator B ID (higher)")
    shared_chatters: int = Field(..., description="Chatters common to both audiences")
    shared_regulars: int = Field(..., description="Regulars common to both audiences")
    jaccard_chatters: Optional[float] = Field(
        None, description="shared / union of chatters, rounded to 4 places; null when union is 0"
    )
    jaccard_regulars: Optional[float] = Field(
        None, description="shared / union of regulars, rounded to 4 places; null when union is 0"
    )


class CommunityOverlap(BaseModel):
    """Overlap map for the top creators by audience size."""

    creators: List[OverlapCreator] = Field(..., description="Top creators by audience size")
    pairs: List[OverlapPair] = Field(..., description="Overlap pairs restricted to those creators")
    computed_at: Optional[str] = Field(
        None, description="When the overlap rollup was last computed (ISO 8601); null when empty"
    )


class CreatorNeighbor(BaseModel):
    """One "audience also watches" neighbor for a creator."""

    creator_id: int = Field(..., description="Neighbor creator ID", json_schema_extra={"example": 8})
    nick: str = Field(..., description="Neighbor login/nick")
    display_name: str = Field(..., description="Neighbor display name")
    shared_chatters: int = Field(..., description="Chatters shared with the queried creator")
    shared_regulars: int = Field(..., description="Regulars shared with the queried creator")


class CreatorNeighbors(BaseModel):
    """Ranked "audience also watches" neighbors for one creator."""

    creator_id: int = Field(..., description="Queried creator ID", json_schema_extra={"example": 5})
    metric: str = Field(..., description="Ranking metric: chatters or regulars")
    neighbors: List[CreatorNeighbor] = Field(..., description="Neighbors ranked by the metric")
