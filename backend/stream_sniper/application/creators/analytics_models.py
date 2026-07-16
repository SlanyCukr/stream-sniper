"""Canonical read models for creator-level analytics."""

from pydantic import AliasChoices, BaseModel, Field


class TrendPoint(BaseModel):
    """Per-stream metrics for one point on a creator's trend line."""

    stream_id: int = Field(..., description="Stream ID", json_schema_extra={"example": 42})
    title: str = Field(..., description="Stream title")
    start: str = Field(..., description="Stream start timestamp (ISO 8601)")
    duration_seconds: int | None = Field(None, description="Stream duration in seconds, if known")
    message_count: int = Field(..., description="Total messages in the stream")
    messages_per_minute: float = Field(..., description="Average messages per minute")
    unique_chatters: int = Field(..., description="Distinct chatters in the stream")
    new_chatters: int = Field(..., description="First-time chatters for this creator")
    returning_chatters: int = Field(..., description="Chatters seen in an earlier stream")


class CreatorTrends(BaseModel):
    """A creator's recent streams as a trend series (ascending by start)."""

    creator_id: int = Field(..., description="Creator ID", json_schema_extra={"example": 5})
    points: list[TrendPoint] = Field(..., description="Trend points, ascending by start")


class LatestCreatorStream(BaseModel):
    """Most recent captured stream linked from a creator dossier."""

    stream_id: int
    title: str
    start: str | None = None


class CreatorSummary(BaseModel):
    """Identity and lifetime rollup summary used by the permanent creator page."""

    creator_id: int
    nick: str
    display_name: str
    profile_image_url: str | None = None
    twitch_user_id: str | None = Field(
        None,
        validation_alias=AliasChoices("twitch_user_id", "twitch_id"),
        serialization_alias="twitch_id",
    )
    total_streams: int
    first_stream_at: str | None = None
    last_stream_at: str | None = None
    total_messages: int
    duration_seconds: int | None = None
    messages_per_minute: float | None = None
    audience_size: int
    regulars: int
    latest_stream: LatestCreatorStream | None = None
