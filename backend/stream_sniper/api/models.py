"""Shared response contracts for the public Stream Sniper API."""

from typing import Any, List

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard API error response."""

    detail: str = Field(..., description="Error message", json_schema_extra={"example": "Stream not found"})


class ChatterMessagesResponse(BaseModel):
    """Paginated cross-stream chatter message log."""

    messages: List[List[Any]] = Field(
        ..., description="List of [stream_id, stream_title, streamer_display_name, text, timestamp] tuples"
    )
    total: int = Field(..., description="Total messages sent by the chatter", json_schema_extra={"example": 1234})


class StreamsResponse(BaseModel):
    """Paginated list of streams."""

    streams: List[List[Any]] = Field(..., description="List of stream data tuples")
    max_offset: int = Field(..., description="Maximum offset for pagination", json_schema_extra={"example": 1000})


class StreamDetails(BaseModel):
    """Detailed analytics for one stream."""

    csi: List[Any] = Field(..., description="Comprehensive stream info tuple")
    mac: List[List[Any]] = Field(..., description="Most active chatters")
    mtc: List[List[Any]] = Field(..., description="Most tagged chatters")
    octw: List[List[Any]] = Field(..., description="Other creators that wrote in stream")
    cis: List[List[Any]] = Field(..., description="Chatters in stream")
