"""Canonical Creator Wrapped read models (a single creator's period recap).

Application-owned Pydantic (FastAPI-free), mirroring ``scenes/wrapped_models.py``
scoped to one creator: totals, top chatters, top moments, top copypastas, and top
emotes over a trailing window. There is no ``creators_active``/``top_creators``
section (single-creator scope makes both trivial) and no ``notable_events`` section
(scene events are cross-creator by design). Fields that would be constant for a
single creator are dropped from the nested rows too: chatters carry no
``creators_visited``/``home_creator_display_name`` (always 1 / this creator), moments
carry no ``creator_display_name``, and copypastas carry no ``creator_count`` (always
1, since the source rows are already filtered to this creator).

Nullable fields mean "unknown" and are never coalesced to 0 — a creator with no
streams in the window has ``hours_streamed=None``, not ``0``.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CreatorWrappedTotals(BaseModel):
    streams: int = Field(..., description="Streams that started within the window")
    hours_streamed: float | None = Field(
        None, description="Total streamed hours in the window (null when nothing was streamed)"
    )
    messages: int = Field(..., description="Total chat messages across those streams")
    active_chatters: int = Field(..., description="Distinct human chatters active in the window")


class CreatorWrappedChatter(BaseModel):
    rank: int = Field(..., description="1-based rank by total messages")
    chatter_id: int
    nick: str
    total_messages: int = Field(..., description="Messages the chatter sent to this creator in the window")
    streams_attended: int = Field(..., description="This creator's distinct streams the chatter attended")


class CreatorWrappedMoment(BaseModel):
    stream_id: int
    stream_title: str
    twitch_id: str | None = Field(None, description="Twitch VOD id, if known")
    bucket_minute: str = Field(..., description="Minute the moment peaked (ISO 8601)")
    offset_seconds: int = Field(..., description="Seconds into the VOD")
    ratio: float | None = Field(None, description="Spike ratio vs baseline (null = no baseline)")
    message_count: int = Field(..., description="Messages in the peak minute")


class CreatorWrappedCopypasta(BaseModel):
    message_text_id: int
    text: str
    usage_count: int = Field(..., description="Total sends across the window, this creator's streams only")
    stream_count: int = Field(..., description="This creator's distinct streams the copypasta appeared in")


class CreatorWrappedEmote(BaseModel):
    emote_id: int
    name: str
    source: str = Field(..., description="Emote provider: bttv or twitch")
    usage: int = Field(..., description="Total emote uses across the window")
    chatter_reach: int = Field(..., description="Sum of per-stream chatter_count over the window")


class CreatorWrapped(BaseModel):
    creator_id: int
    days: int = Field(..., description="Length of the recap window in days")
    totals: CreatorWrappedTotals
    top_chatters: list[CreatorWrappedChatter] = Field(
        ..., description="Top chatters by messages, bots excluded (up to 5)"
    )
    top_moments: list[CreatorWrappedMoment] = Field(..., description="Highest-hype moments (up to 3)")
    top_copypastas: list[CreatorWrappedCopypasta] = Field(..., description="Most-used copypastas (up to 3)")
    top_emotes: list[CreatorWrappedEmote] = Field(..., description="Most-used emotes (up to 5)")
