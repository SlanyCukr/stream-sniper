"""Shared response contracts for the public Stream Sniper API."""

from typing import Any, Dict, List, Optional

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


class HealthStatusResponse(BaseModel):
    """Basic health status for load balancers and probes."""

    status: str = Field(..., description="Overall health status", json_schema_extra={"example": "healthy"})
    database: Optional[Dict[str, Any]] = Field(None, description="Database connection pool status")
    timestamp: str = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version", json_schema_extra={"example": "1.0.0"})
    uptime_seconds: Optional[float] = Field(None, description="Application uptime in seconds")
    error: Optional[str] = Field(None, description="Error detail when the health check itself fails")


class DetailedHealthStatusResponse(BaseModel):
    """Detailed component and system health status."""

    status: str = Field(..., description="Overall health status", json_schema_extra={"example": "healthy"})
    timestamp: str = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version", json_schema_extra={"example": "1.0.0"})
    uptime_seconds: float = Field(..., description="Application uptime in seconds")
    components: Dict[str, Any] = Field(..., description="Component health status")
    system: Dict[str, Any] = Field(..., description="System metrics and information")


class MetricsResponse(BaseModel):
    """API performance and monitoring data."""

    system: Dict[str, Any] = Field(..., description="System metrics")
    requests: Dict[str, Any] = Field(..., description="Request statistics")
    cache: Dict[str, Any] = Field(..., description="Cache performance metrics")
    rate_limiting: Dict[str, Any] = Field(..., description="Rate limiting metrics")
    endpoints: Dict[str, Any] = Field(..., description="Per-endpoint statistics")
