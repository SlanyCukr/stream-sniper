"""Response contracts for creator-level analytics endpoints."""

from typing import List, Optional

from pydantic import BaseModel, Field


class TrendPoint(BaseModel):
    """Per-stream metrics for one point on a creator's trend line."""

    stream_id: int = Field(..., description="Stream ID", json_schema_extra={"example": 42})
    title: str = Field(..., description="Stream title")
    start: str = Field(..., description="Stream start timestamp (ISO 8601)")
    duration_seconds: Optional[int] = Field(None, description="Stream duration in seconds, if known")
    message_count: int = Field(..., description="Total messages in the stream")
    messages_per_minute: float = Field(..., description="Average messages per minute")
    unique_chatters: int = Field(..., description="Distinct chatters in the stream")
    new_chatters: int = Field(..., description="First-time chatters for this creator")
    returning_chatters: int = Field(..., description="Chatters seen in an earlier stream")


class CreatorTrends(BaseModel):
    """A creator's recent streams as a trend series (ascending by start)."""

    creator_id: int = Field(..., description="Creator ID", json_schema_extra={"example": 5})
    points: List[TrendPoint] = Field(..., description="Trend points, ascending by start")


class Regular(BaseModel):
    """A recurring chatter in a creator's audience."""

    chatter_id: int = Field(..., description="Chatter ID", json_schema_extra={"example": 42})
    nick: str = Field(..., description="Chatter nickname")
    streams_attended: int = Field(..., description="Number of the creator's streams attended")
    attendance_rate: float = Field(..., description="streams_attended / total_streams, rounded to 4 places")
    first_seen: str = Field(..., description="First time seen for this creator (ISO 8601)")
    last_seen: str = Field(..., description="Most recent time seen for this creator (ISO 8601)")
    last_stream_attended: int = Field(..., description="ID of the most recent stream attended")
    message_count: int = Field(..., description="Total messages sent across the creator's streams")


class CreatorRegulars(BaseModel):
    """A creator's recurring chatters, ranked by attendance."""

    creator_id: int = Field(..., description="Creator ID", json_schema_extra={"example": 5})
    total_streams: int = Field(..., description="Total streams for this creator (attendance denominator)")
    regulars: List[Regular] = Field(..., description="Recurring chatters")


class LatestCreatorStream(BaseModel):
    """Most recent captured stream linked from a creator dossier."""

    stream_id: int
    title: str
    start: Optional[str] = None


class CreatorSummary(BaseModel):
    """Identity and lifetime rollup summary used by the permanent creator page."""

    creator_id: int
    nick: str
    display_name: str
    profile_image_url: Optional[str] = None
    twitch_id: Optional[str] = None
    total_streams: int
    first_stream_at: Optional[str] = None
    last_stream_at: Optional[str] = None
    total_messages: int
    duration_seconds: Optional[int] = None
    messages_per_minute: Optional[float] = None
    audience_size: int
    regulars: int
    latest_stream: Optional[LatestCreatorStream] = None
