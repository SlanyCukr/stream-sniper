"""Contracts for windowed audience participation movement."""

from typing import List, Optional

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
    retention_rate: Optional[float] = None
    gain_rate: Optional[float] = None
    prior_channels_for_gained: List[AudienceAssociation]
    current_channels_for_lapsed: List[AudienceAssociation]
