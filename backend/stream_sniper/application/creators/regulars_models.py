"""Canonical creator-regulars read models shared with the API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from stream_sniper.database.gateways.creators.records import CreatorRegularRow


class Regular(BaseModel):
    chatter_id: int = Field(..., description="Chatter ID")
    nick: str = Field(..., description="Chatter nickname")
    streams_attended: int = Field(..., description="Number of the creator's streams attended")
    attendance_rate: float = Field(..., description="streams_attended / total_streams, rounded to 4 places")
    first_seen: str = Field(..., description="First time seen for this creator")
    last_seen: str = Field(..., description="Most recent time seen for this creator")
    last_stream_attended: int = Field(..., description="ID of the most recent stream attended")
    message_count: int = Field(..., description="Total messages sent across the creator's streams")

    @classmethod
    def from_row(cls, row: CreatorRegularRow, *, total_streams: int) -> Regular:
        return cls(
            chatter_id=row.chatter_id,
            nick=row.nick,
            streams_attended=row.streams_attended,
            attendance_rate=round(row.streams_attended / total_streams, 4) if total_streams else 0.0,
            first_seen=row.first_seen,
            last_seen=row.last_seen,
            last_stream_attended=row.last_stream_attended,
            message_count=row.message_count,
        )


class CreatorRegulars(BaseModel):
    creator_id: int = Field(..., description="Creator ID")
    total_streams: int = Field(..., description="Attendance denominator for this creator")
    regulars: list[Regular] = Field(..., description="Recurring chatters")
