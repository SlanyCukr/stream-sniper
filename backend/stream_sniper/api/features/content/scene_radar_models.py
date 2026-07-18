"""Response contracts for the live Moment Radar (chat velocity on currently-live streams).

Nullable = unknown throughout: ``baseline_per_minute`` / ``ratio`` are null (never 0) when there
is not enough recent history to compute them. ``spiking`` uses the persisted-moment threshold
(``messages >= max(SPIKE_MULTIPLIER * baseline, MIN_ABSOLUTE)``), so a cold-start burst with no
baseline still fires via the absolute floor even while ratio stays null. Every timestamp is a
second-precision wire string (``WIRE_TS_FORMAT``).
"""

from pydantic import BaseModel, Field


class RadarMinute(BaseModel):
    """One completed minute in a stream's trailing velocity series (zero-filled if silent)."""

    minute: str = Field(..., description="Completed minute, floored (ISO 8601 wire timestamp)")
    messages: int = Field(..., description="Messages sent in this minute (0 for a silent minute)")


class RadarChannel(BaseModel):
    """One currently-live stream with its last-minute velocity, baseline, and spike verdict."""

    stream_id: int = Field(..., description="Stream ID")
    creator_id: int = Field(..., description="Creator ID")
    creator_nick: str = Field(..., description="Creator login/nick")
    creator_display_name: str = Field(..., description="Creator display name")
    profile_image_url: str | None = Field(None, description="Creator avatar URL; null when unknown")
    stream_title: str | None = Field(None, description="Stream title; null when unknown")
    started_at: str | None = Field(None, description="Stream start (ISO 8601); null when unknown")
    messages_last_minute: int = Field(
        ...,
        description=(
            "Messages in the last COMPLETED minute (the current in-progress minute is partial and "
            "excluded)"
        ),
    )
    unique_chatters_last_minute: int = Field(
        ..., description="Distinct chatters in the last completed minute"
    )
    baseline_per_minute: float | None = Field(
        None,
        description=(
            "Median messages/minute over the NONZERO history minutes (trailing window excluding "
            "the last minute — the typical rate while chat is active); null when fewer than 3 "
            "nonzero-history minutes"
        ),
    )
    ratio: float | None = Field(
        None,
        description="messages_last_minute / baseline_per_minute (2 dp); null when baseline is null or 0",
    )
    spiking: bool = Field(
        ...,
        description=(
            "True when messages_last_minute >= max(3.0 * baseline, 15) — exactly the persisted-"
            "moment thresholds (SPIKE_MULTIPLIER / MIN_ABSOLUTE). Fires on the absolute floor "
            "even when baseline/ratio are null (cold start)"
        ),
    )
    minutes: list[RadarMinute] = Field(
        ..., description="Trailing 15 completed minutes, ascending and zero-filled"
    )


class SceneRadar(BaseModel):
    """The live Moment Radar snapshot: every currently-live stream, spikes first."""

    generated_at: str = Field(..., description="Snapshot time, second-precision ISO 8601 (UTC)")
    channels: list[RadarChannel] = Field(..., description="Live streams, spiking first then busiest")
