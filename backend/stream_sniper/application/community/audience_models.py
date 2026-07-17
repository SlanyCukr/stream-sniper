"""Contracts for windowed audience participation movement."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from stream_sniper.database.gateways.community.records import AudienceAssociationRow


class AudienceAssociation(BaseModel):
    creator_id: int
    nick: str
    display_name: str
    chatter_count: int

    @classmethod
    def from_row(cls, row: AudienceAssociationRow) -> AudienceAssociation:
        return cls(
            creator_id=row.creator_id,
            nick=row.nick,
            display_name=row.display_name,
            chatter_count=row.chatter_count,
        )


class AudienceMovement(BaseModel):
    creator_id: int
    window_days: int
    current_audience: int
    previous_audience: int
    retained: int
    gained: int
    lapsed: int
    retention_rate: float | None = None
    gain_rate: float | None = None
    prior_channels_for_gained: list[AudienceAssociation]
    current_channels_for_lapsed: list[AudienceAssociation]
