"""Response contracts for the scene chatter power-rankings endpoint."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from ....application.chatters.archetypes import compute_archetypes
from ....application.chatters.passport_models import PassportArchetype, share_of_total

if TYPE_CHECKING:
    from ....database.gateways.creators.scene_chatter_rankings_gateway import SceneChatterRankRow


class RankHomeChannel(BaseModel):
    creator_id: int = Field(..., description="Creator the chatter sends the most messages to (in-window)")
    creator_nick: str = Field(..., description="Creator nickname")
    creator_display_name: str = Field(..., description="Creator display name")
    messages: int = Field(..., description="Messages the chatter sent this creator within the window")
    share: float = Field(..., description="messages / total_messages, rounded to 4 places")


class RankItem(BaseModel):
    rank: int = Field(..., description="1-based rank across the whole window (offset-aware)")
    chatter_id: int = Field(..., description="Chatter ID")
    nick: str = Field(..., description="Chatter nickname")
    total_messages: int = Field(..., description="Messages sent across the window")
    streams_attended: int = Field(..., description="Distinct streams the chatter appeared in")
    creators_visited: int = Field(..., description="Distinct creators the chatter chatted in")
    home_channel: RankHomeChannel | None = Field(
        None, description="The creator the chatter chats in most within the window"
    )
    archetypes: list[PassportArchetype] = Field(
        default_factory=list,
        description=(
            "Rule-based identity badges derived from ACCOUNT-WIDE aggregates "
            "(never the window slice — badges must not flip with the ranking window)"
        ),
    )

    @classmethod
    def from_row(cls, row: SceneChatterRankRow, *, rank: int, now: datetime | None = None) -> RankItem:
        home = None
        if row.home_creator_id is not None:
            home = RankHomeChannel(
                creator_id=row.home_creator_id,
                creator_nick=row.home_creator_nick or "",
                creator_display_name=row.home_creator_display_name or "",
                messages=row.home_messages or 0,
                share=share_of_total(row.home_messages or 0, row.total_messages),
            )
        # Identity badges read the lifetime aggregates, NOT the window slice above:
        # a lifetime loyalist who spread out for one week must not badge as Wanderer
        # on the 7-day tab (the gateway carries lifetime_* account-wide in both paths).
        lifetime_home_share = (
            share_of_total(row.lifetime_home_messages, row.lifetime_messages)
            if row.lifetime_home_messages is not None
            else None
        )
        archetypes = compute_archetypes(
            total_messages=row.lifetime_messages,
            streams_attended=row.lifetime_streams,
            creators_visited=row.lifetime_creators,
            home_share=lifetime_home_share,
            first_seen=row.first_seen,
            now=now if now is not None else datetime.now(UTC),
        )
        return cls(
            rank=rank,
            chatter_id=row.chatter_id,
            nick=row.nick,
            total_messages=row.total_messages,
            streams_attended=row.streams_attended,
            creators_visited=row.creators_visited,
            home_channel=home,
            archetypes=archetypes,
        )


class SceneChatterRankings(BaseModel):
    window: str = Field(..., description="Window selector: 'all', '7', or '30'")
    items: list[RankItem] = Field(..., description="Ranked chatters, most messages first")
    has_more: bool = Field(..., description="Whether another page exists after this one")
