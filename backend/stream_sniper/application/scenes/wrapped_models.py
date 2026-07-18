"""Canonical Scene Wrapped read models (the period recap).

Application-owned Pydantic (FastAPI-free): a single recap over a trailing window,
assembled from several scene gateways in :mod:`wrapped_query`. Nullable fields mean
"unknown" and are never coalesced to 0 — an un-rolled creator's ``msgs_per_min`` or a
creator with no live samples' ``peak_viewers`` surface as ``null``, not zero.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class WrappedTotals(BaseModel):
    streams: int = Field(..., description="Streams that started within the window")
    hours_streamed: float | None = Field(
        None, description="Total streamed hours in the window (null when nothing was streamed)"
    )
    messages: int = Field(..., description="Total chat messages across those streams")
    active_chatters: int = Field(..., description="Distinct human chatters active in the window")
    creators_active: int = Field(..., description="Creators with at least one stream in the window")


class WrappedCreator(BaseModel):
    rank: int = Field(..., description="1-based rank by total messages")
    creator_id: int
    nick: str
    display_name: str
    profile_image_url: str | None = Field(None, description="Creator avatar URL, if known")
    total_messages: int = Field(..., description="Total chat messages across the creator's streams")
    streams: int = Field(..., description="Streams in the window")
    hours_streamed: float | None = Field(None, description="Streamed hours in the window (null = unknown)")
    msgs_per_min: float | None = Field(None, description="Messages per minute (null when not yet rolled up)")
    peak_viewers: int | None = Field(None, description="Peak live viewers in the window (null = no samples)")


class WrappedChatter(BaseModel):
    rank: int = Field(..., description="1-based rank by total messages")
    chatter_id: int
    nick: str
    total_messages: int = Field(..., description="Messages the chatter sent in the window")
    streams_attended: int = Field(..., description="Distinct streams attended in the window")
    creators_visited: int = Field(..., description="Distinct creators chatted in during the window")
    home_creator_display_name: str | None = Field(
        None, description="Creator the chatter sent the most messages to in the window"
    )


class WrappedMoment(BaseModel):
    stream_id: int
    stream_title: str
    twitch_id: str | None = Field(None, description="Twitch VOD id, if known")
    creator_display_name: str
    bucket_minute: str = Field(..., description="Minute the moment peaked (ISO 8601)")
    offset_seconds: int = Field(..., description="Seconds into the VOD")
    ratio: float | None = Field(None, description="Spike ratio vs baseline (null = no baseline)")
    message_count: int = Field(..., description="Messages in the peak minute")


class WrappedCopypasta(BaseModel):
    message_text_id: int
    text: str
    usage_count: int = Field(..., description="Total sends across the window")
    creator_count: int = Field(..., description="Distinct creators the copypasta appeared in")
    stream_count: int = Field(..., description="Distinct streams the copypasta appeared in")


class WrappedEmote(BaseModel):
    emote_id: int
    name: str
    source: str = Field(..., description="Emote provider: bttv or twitch")
    usage: int = Field(..., description="Total emote uses across the window")
    chatter_reach: int = Field(..., description="Sum of per-stream chatter_count over the window")


class WrappedEvent(BaseModel):
    event_type: str
    occurred_at: str = Field(..., description="When the event happened (ISO 8601)")
    title: str
    summary: str
    creator_display_name: str | None = Field(None, description="Creator involved, if any")


class SceneWrapped(BaseModel):
    days: int = Field(..., description="Length of the recap window in days")
    totals: WrappedTotals
    top_creators: list[WrappedCreator] = Field(..., description="Top creators by messages (up to 5)")
    top_chatters: list[WrappedChatter] = Field(..., description="Top chatters by messages, bots excluded (up to 5)")
    top_moments: list[WrappedMoment] = Field(..., description="Highest-hype moments (up to 3)")
    top_copypastas: list[WrappedCopypasta] = Field(..., description="Most-used copypastas (up to 3)")
    top_emotes: list[WrappedEmote] = Field(..., description="Most-used emotes (up to 5)")
    notable_events: list[WrappedEvent] = Field(..., description="Notable scene events, newest first (up to 8)")
