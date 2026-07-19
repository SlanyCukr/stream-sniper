"""Read contract for the single-emote drill-down (the /emotes/[id] page)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from stream_sniper.database.gateways.analytics.emote_detail_gateway import (
        EmoteCreatorUsageRow,
        EmoteMetaRow,
        EmoteStreamUsageRow,
        EmoteTotalsRow,
        EmoteWeeklyUsageRow,
    )


class EmoteMeta(BaseModel):
    emote_id: int
    name: str
    source: str = Field(..., description="Emote provider: bttv or twitch")
    provider_id: str | None = None
    first_seen: str | None = Field(None, description="Dictionary first-seen time (ISO 8601), if known")

    @classmethod
    def from_row(cls, row: EmoteMetaRow) -> EmoteMeta:
        return cls(
            emote_id=row.emote_id,
            name=row.name,
            source=row.source,
            provider_id=row.provider_id,
            first_seen=row.first_seen,
        )


class EmoteTotals(BaseModel):
    """Lifetime aggregates; all-zero with null last_used when the emote was never used."""

    usage: int
    chatter_reach: int = Field(..., description="Sum of per-stream chatter counts (attendance-weighted)")
    stream_count: int
    creator_count: int
    last_used: str | None = Field(None, description="Start time of the newest stream it appeared in")

    @classmethod
    def from_row(cls, row: EmoteTotalsRow) -> EmoteTotals:
        return cls(
            usage=row.usage,
            chatter_reach=row.chatter_reach,
            stream_count=row.stream_count,
            creator_count=row.creator_count,
            last_used=row.last_used,
        )


class EmoteCreatorUsage(BaseModel):
    creator_id: int
    nick: str
    display_name: str
    usage: int
    chatter_reach: int
    stream_count: int

    @classmethod
    def from_row(cls, row: EmoteCreatorUsageRow) -> EmoteCreatorUsage:
        return cls(
            creator_id=row.creator_id,
            nick=row.nick,
            display_name=row.display_name,
            usage=row.usage,
            chatter_reach=row.chatter_reach,
            stream_count=row.stream_count,
        )


class EmoteWeeklyUsage(BaseModel):
    week_start: str = Field(..., description="ISO date of the week's Monday")
    usage: int

    @classmethod
    def from_row(cls, row: EmoteWeeklyUsageRow) -> EmoteWeeklyUsage:
        return cls(week_start=row.week_start, usage=row.usage)


class EmoteStreamUsage(BaseModel):
    stream_id: int
    title: str | None = None
    start: str | None = None
    creator_id: int
    creator_nick: str
    creator_display_name: str
    usage: int
    chatter_count: int

    @classmethod
    def from_row(cls, row: EmoteStreamUsageRow) -> EmoteStreamUsage:
        return cls(
            stream_id=row.stream_id,
            title=row.title,
            start=row.start,
            creator_id=row.creator_id,
            creator_nick=row.creator_nick,
            creator_display_name=row.creator_display_name,
            usage=row.usage,
            chatter_count=row.chatter_count,
        )


class EmoteDetail(BaseModel):
    """The full drill-down; list sections are empty (not null) for an unused emote."""

    meta: EmoteMeta
    totals: EmoteTotals
    top_creators: list[EmoteCreatorUsage]
    weekly_usage: list[EmoteWeeklyUsage] = Field(
        ..., description="Trailing weeks with any usage, oldest first; absent weeks mean zero"
    )
    recent_streams: list[EmoteStreamUsage]
