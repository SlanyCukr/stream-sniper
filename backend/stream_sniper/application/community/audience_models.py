"""Contracts for windowed audience participation movement."""

from pydantic import BaseModel


class AudienceAssociation(BaseModel):
    creator_id: int
    nick: str
    display_name: str
    chatter_count: int


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
