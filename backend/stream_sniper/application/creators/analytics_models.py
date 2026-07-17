"""Canonical read models for creator-level analytics."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import AliasChoices, BaseModel, Field

if TYPE_CHECKING:
    from stream_sniper.database.gateways.analytics.records import CreatorTrendRow
    from stream_sniper.database.gateways.identity.records import CreatorSummaryRow


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

    @classmethod
    def from_row(cls, row: CreatorTrendRow) -> TrendPoint:
        return cls(
            stream_id=row.stream_id,
            title=row.title,
            start=row.start,
            duration_seconds=row.duration_seconds,
            message_count=row.message_count,
            messages_per_minute=row.messages_per_minute,
            unique_chatters=row.unique_chatters,
            new_chatters=row.new_chatters,
            returning_chatters=row.returning_chatters,
        )


class CreatorTrends(BaseModel):
    """A creator's recent streams as a trend series (ascending by start)."""

    creator_id: int = Field(..., description="Creator ID", json_schema_extra={"example": 5})
    points: list[TrendPoint] = Field(..., description="Trend points, ascending by start")


class LatestCreatorStream(BaseModel):
    """Most recent captured stream linked from a creator dossier."""

    stream_id: int
    title: str
    start: str | None = None

    @classmethod
    def from_summary_row(cls, row: CreatorSummaryRow) -> LatestCreatorStream | None:
        """Project the latest-stream columns of a summary row, or None when absent."""
        if row.latest_stream_id is None:
            return None
        return cls(
            stream_id=row.latest_stream_id,
            title=row.latest_stream_title or "",
            start=row.latest_stream_start,
        )


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

    @classmethod
    def from_row(cls, row: CreatorSummaryRow) -> CreatorSummary:
        return cls(
            creator_id=row.creator_id,
            nick=row.nick,
            display_name=row.display_name,
            profile_image_url=row.profile_image_url,
            twitch_user_id=str(row.twitch_user_id) if row.twitch_user_id is not None else None,
            total_streams=row.total_streams,
            first_stream_at=row.first_stream_at,
            last_stream_at=row.last_stream_at,
            total_messages=row.total_messages,
            duration_seconds=row.duration_seconds,
            messages_per_minute=row.messages_per_minute,
            audience_size=row.audience_size,
            regulars=row.regulars,
            latest_stream=LatestCreatorStream.from_summary_row(row),
        )
