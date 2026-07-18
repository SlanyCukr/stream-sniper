"""Canonical chatter-passport read models shared with the API.

A passport is a public per-chatter identity profile assembled from the
creator_chatter_stats and stream_chatter_stats rollups plus the chatter table.
``share`` fields are ``messages / totals.messages`` rounded to 4 places.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from stream_sniper.database.gateways.analytics.records import (
        ChatterActiveStreamRow,
        ChatterDebutRow,
    )
    from stream_sniper.database.gateways.chat.records import ChatterProfileRow
    from stream_sniper.database.gateways.community.records import ChatCompanionRow
    from stream_sniper.database.gateways.creators.records import ChatterLoyaltyRow


def _share(messages: int, total_messages: int) -> float:
    """messages / total_messages rounded to 4 places (0.0 when the corpus is empty)."""
    return round(messages / total_messages, 4) if total_messages else 0.0


class PassportChatter(BaseModel):
    id: int = Field(..., description="Chatter ID")
    nick: str = Field(..., description="Chatter nickname")
    is_bot: bool | None = Field(None, description="Bot flag (NULL = not yet classified)")
    bot_reason: str | None = Field(None, description="Why the chatter was flagged, if any")

    @classmethod
    def from_row(cls, row: ChatterProfileRow) -> PassportChatter:
        return cls(id=row.id, nick=row.nick, is_bot=row.is_bot, bot_reason=row.bot_reason)


class PassportTotals(BaseModel):
    messages: int = Field(..., description="Total messages across every creator")
    streams_attended: int = Field(..., description="Total streams attended across every creator")
    creators_visited: int = Field(..., description="Distinct creators the chatter has chatted in")
    first_seen: str | None = Field(None, description="Earliest first-seen across creators (NULL = unknown)")
    last_seen: str | None = Field(None, description="Latest last-seen across creators (NULL = unknown)")


class PassportDebut(BaseModel):
    stream_id: int = Field(..., description="Stream of the chatter's first message")
    stream_title: str = Field(..., description="Title of that stream")
    creator_display_name: str = Field(..., description="Creator of that stream")
    time: str = Field(..., description="Timestamp of the first message")

    @classmethod
    def from_row(cls, row: ChatterDebutRow) -> PassportDebut:
        return cls(
            stream_id=row.stream_id,
            stream_title=row.stream_title,
            creator_display_name=row.creator_display_name,
            time=row.time,
        )


class PassportHomeChannel(BaseModel):
    creator_id: int = Field(..., description="Creator the chatter sends the most messages to")
    creator_nick: str = Field(..., description="Creator nickname")
    creator_display_name: str = Field(..., description="Creator display name")
    messages: int = Field(..., description="Messages the chatter sent this creator")
    share: float = Field(..., description="messages / totals.messages, rounded to 4 places")

    @classmethod
    def from_row(cls, row: ChatterLoyaltyRow, *, total_messages: int) -> PassportHomeChannel:
        return cls(
            creator_id=row.creator_id,
            creator_nick=row.creator_nick,
            creator_display_name=row.creator_display_name,
            messages=row.message_count,
            share=_share(row.message_count, total_messages),
        )


class PassportLoyalty(BaseModel):
    creator_id: int = Field(..., description="Creator the chatter chatted in")
    creator_nick: str = Field(..., description="Creator nickname")
    creator_display_name: str = Field(..., description="Creator display name")
    messages: int = Field(..., description="Messages the chatter sent this creator")
    streams_attended: int = Field(..., description="Creator's streams the chatter attended")
    share: float = Field(..., description="messages / totals.messages, rounded to 4 places")

    @classmethod
    def from_row(cls, row: ChatterLoyaltyRow, *, total_messages: int) -> PassportLoyalty:
        return cls(
            creator_id=row.creator_id,
            creator_nick=row.creator_nick,
            creator_display_name=row.creator_display_name,
            messages=row.message_count,
            streams_attended=row.streams_attended,
            share=_share(row.message_count, total_messages),
        )


class PassportMostActiveStream(BaseModel):
    stream_id: int = Field(..., description="Stream the chatter was most active in")
    title: str = Field(..., description="Title of that stream")
    creator_display_name: str = Field(..., description="Creator of that stream")
    messages: int = Field(..., description="Messages the chatter sent in that stream")

    @classmethod
    def from_row(cls, row: ChatterActiveStreamRow) -> PassportMostActiveStream:
        return cls(
            stream_id=row.stream_id,
            title=row.title,
            creator_display_name=row.creator_display_name,
            messages=row.message_count,
        )


class PassportMilestones(BaseModel):
    most_active_stream: PassportMostActiveStream | None = Field(
        None, description="The single stream the chatter sent the most messages in"
    )


class PassportCompanion(BaseModel):
    chatter_id: int = Field(..., description="Co-chatter's chatter ID")
    nick: str = Field(..., description="Co-chatter's nickname")
    shared_streams: int = Field(..., description="Streams both chatters attended")

    @classmethod
    def from_row(cls, row: ChatCompanionRow) -> PassportCompanion:
        return cls(chatter_id=row.chatter_id, nick=row.nick, shared_streams=row.shared_streams)


class PassportArchetype(BaseModel):
    key: str = Field(..., description="Stable archetype identifier (e.g. 'loyalist')")
    label: str = Field(..., description="Human-readable badge label")
    description: str = Field(..., description="Plain-language reason the badge applies (threshold summary)")


class ChatterPassport(BaseModel):
    chatter: PassportChatter
    totals: PassportTotals
    debut: PassportDebut | None = Field(None, description="The chatter's first message in the corpus")
    home_channel: PassportHomeChannel | None = Field(None, description="The creator the chatter chats in most")
    loyalty: list[PassportLoyalty] = Field(..., description="Every creator chatted in, most messages first")
    milestones: PassportMilestones
    archetypes: list[PassportArchetype] = Field(
        default_factory=list, description="Rule-based identity badges derived from the passport's own data"
    )
    companions: list[PassportCompanion] = Field(
        default_factory=list, description="Top co-chatters ranked by shared-stream count, bots excluded"
    )
