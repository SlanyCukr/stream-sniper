"""Canonical creator-regulars read models shared with the API."""

from pydantic import BaseModel, Field


class Regular(BaseModel):
    chatter_id: int = Field(..., description="Chatter ID")
    nick: str = Field(..., description="Chatter nickname")
    streams_attended: int = Field(..., description="Number of the creator's streams attended")
    attendance_rate: float = Field(..., description="streams_attended / total_streams, rounded to 4 places")
    first_seen: str = Field(..., description="First time seen for this creator")
    last_seen: str = Field(..., description="Most recent time seen for this creator")
    last_stream_attended: int = Field(..., description="ID of the most recent stream attended")
    message_count: int = Field(..., description="Total messages sent across the creator's streams")


class CreatorRegulars(BaseModel):
    creator_id: int = Field(..., description="Creator ID")
    total_streams: int = Field(..., description="Attendance denominator for this creator")
    regulars: list[Regular] = Field(..., description="Recurring chatters")
