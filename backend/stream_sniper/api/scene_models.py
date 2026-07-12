"""Response contracts for the scene endpoints (live-now, leaderboard, copypasta library)."""

from typing import List, Optional

from pydantic import BaseModel, Field


class LiveStreamer(BaseModel):
    """One currently-live tracked streamer, from the latest fresh viewer sample."""

    creator_id: int = Field(..., description="Creator ID", json_schema_extra={"example": 5})
    nick: str = Field(..., description="Creator login/nick")
    display_name: str = Field(..., description="Creator display name")
    profile_image_url: Optional[str] = Field(None, description="Creator avatar URL, if known")
    viewer_count: int = Field(..., description="Live viewer count at the latest sample")
    title: Optional[str] = Field(None, description="Stream title at the latest sample, if known")
    session_started_at: Optional[str] = Field(
        None, description="Live session start (ISO 8601, UTC); uptime anchor, null if unknown"
    )
    sampled_at: str = Field(..., description="When the latest sample was taken (ISO 8601, UTC)")


class SceneLive(BaseModel):
    """The set of tracked streamers currently inferred to be live."""

    live: List[LiveStreamer] = Field(..., description="Live streamers, sorted by viewer_count DESC")
    live_count: int = Field(..., description="Number of live streamers")
    last_sample_at: Optional[str] = Field(
        None, description="Newest viewer sample overall (ISO 8601, UTC); stale => tracker down"
    )


class LeaderboardEntry(BaseModel):
    """One creator's ranked row on the scene leaderboard for the window."""

    rank: int = Field(..., description="1-based rank by total_messages DESC")
    creator_id: int = Field(..., description="Creator ID", json_schema_extra={"example": 5})
    nick: str = Field(..., description="Creator login/nick")
    display_name: str = Field(..., description="Creator display name")
    profile_image_url: Optional[str] = Field(None, description="Creator avatar URL, if known")
    streams: int = Field(..., description="Streams in the window")
    hours_streamed: Optional[float] = Field(
        None, description="Summed hours of closed streams in the window"
    )
    total_messages: int = Field(..., description="Total messages across the window's streams")
    msgs_per_min: Optional[float] = Field(
        None, description="Duration-weighted avg msgs/min; null when no rolled-up data"
    )
    chatter_appearances: int = Field(
        ..., description="Summed per-stream unique chatters (double-counts across streams)"
    )
    peak_viewers: Optional[int] = Field(
        None, description="Max live viewers in the window; null when no samples"
    )


class SceneLeaderboard(BaseModel):
    """Scene-wide creator leaderboard over a fixed window."""

    window_days: int = Field(..., description="Window length in days (7 or 30)")
    entries: List[LeaderboardEntry] = Field(..., description="Ranked creators, best first")


class Copypasta(BaseModel):
    """One deduplicated copypasta/meme message aggregated scene-wide."""

    message_text_id: int = Field(..., description="Deduplicated message-text ID")
    text: str = Field(..., description="The copypasta text")
    usage_count: int = Field(..., description="Total times sent across all streams")
    chatter_appearances: int = Field(
        ..., description="Summed per-stream distinct chatters (double-counts across streams)"
    )
    stream_count: int = Field(..., description="Distinct streams it appeared in")
    creator_count: int = Field(..., description="Distinct creators/channels it spread to")
    first_seen: Optional[str] = Field(None, description="Earliest send time (ISO 8601), if known")
    last_stream_start: Optional[str] = Field(
        None, description="Start of the most recent stream it appeared in (ISO 8601), if known"
    )


class SceneCopypastas(BaseModel):
    """A page of scene-wide copypastas matching the filter."""

    total: int = Field(..., description="Total distinct copypastas matching the filter")
    items: List[Copypasta] = Field(..., description="Copypastas for this page")
