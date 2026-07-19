"""Response contracts for operational health and metrics endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class BasicDatabaseHealthResponse(BaseModel):
    status: str
    healthy: bool
    response_time_ms: float


class HealthStatusResponse(BaseModel):
    """Basic health status for load balancers and probes."""

    status: str = Field(..., description="Overall health status")
    database: BasicDatabaseHealthResponse | None = Field(None, description="Database connection pool status")
    timestamp: str = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version")
    uptime_seconds: float | None = Field(None, description="Application uptime in seconds")
    error: str | None = Field(None, description="Error detail when the check itself fails")


class ComponentHealthResponse(BaseModel):
    status: str
    message: str
    response_time_ms: float
    details: dict[str, Any]
    last_check: str


class ExternalApiHealthResponse(BaseModel):
    twitch: ComponentHealthResponse


class MemoryResourceResponse(BaseModel):
    percent: float
    available_mb: float
    used_mb: float
    total_mb: float


class DiskResourceResponse(BaseModel):
    percent: float
    free_gb: float
    total_gb: float


class SystemResourcesResponse(BaseModel):
    cpu_percent: float
    memory: MemoryResourceResponse
    disk: DiskResourceResponse
    load_average: list[float] | None
    uptime_seconds: float


class DetailedSystemResponse(BaseModel):
    platform: str
    python_version: str
    cpu_count: int | None
    resources: SystemResourcesResponse


class DetailedHealthStatusResponse(BaseModel):
    """Detailed component and system health status."""

    status: str
    timestamp: str
    version: str
    uptime_seconds: float
    components: dict[str, ComponentHealthResponse | ExternalApiHealthResponse]
    system: DetailedSystemResponse
    error: str | None = None


class ApiFeatureFlags(BaseModel):
    caching: bool
    rate_limiting: bool
    compression: bool


class ApiEndpointLinks(BaseModel):
    health: str
    health_detailed: str
    metrics: str
    prometheus_metrics: str
    cache_stats: str


class ApiInfoResponse(BaseModel):
    name: str
    version: str
    description: str
    docs: str
    redoc: str
    features: ApiFeatureFlags
    endpoints: ApiEndpointLinks


class MetricsSystemResponse(BaseModel):
    uptime_seconds: float
    start_time: str
    last_cleanup: str


class RequestMetricsResponse(BaseModel):
    total: int
    per_minute: float
    avg_response_time_ms: float
    status_codes: dict[str, int]


class CacheOperationsResponse(BaseModel):
    hits: int
    misses: int
    sets: int
    deletes: int
    errors: int


class CachePrefixResponse(BaseModel):
    hit_rate: float
    operations: CacheOperationsResponse


class CacheMetricsResponse(BaseModel):
    hit_rate: float
    miss_rate: float
    total_operations: CacheOperationsResponse
    by_prefix: dict[str, CachePrefixResponse]


class RateLimitMetricsResponse(BaseModel):
    total_requests: int
    rate_limited_requests: int
    rate_limit_percentage: float
    endpoint_hits: dict[str, int]


class EndpointMetricsResponse(BaseModel):
    count: int
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    error_rate: float
    cache_hit_rate: float


class MetricsResponse(BaseModel):
    """API performance and monitoring data."""

    system: MetricsSystemResponse
    requests: RequestMetricsResponse
    cache: CacheMetricsResponse
    rate_limiting: RateLimitMetricsResponse
    endpoints: dict[str, EndpointMetricsResponse]


class CacheBackendStatsResponse(BaseModel):
    enabled: bool
    status: str
    backend: str
    stream_sniper_keys: int


class CacheStatsResponse(BaseModel):
    cache_stats: CacheBackendStatsResponse
    performance_metrics: CacheMetricsResponse
    timestamp: str


class CacheFlushResponse(BaseModel):
    message: str
    timestamp: str
