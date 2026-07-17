"""Health-domain contracts: status vocabulary, probe records, and payload shapes.

Policy-neutral data owned by the observability package: probes produce these
records, renderers (``health_renderers``) serialize them, and the checker
(``health``) orchestrates both. Nothing here touches I/O.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, NotRequired, TypedDict


class ComponentHealthPayload(TypedDict):
    status: str
    message: str
    response_time_ms: float
    details: dict[str, Any]
    last_check: str


class ExternalApisPayload(TypedDict):
    twitch: ComponentHealthPayload


class MemoryResourcePayload(TypedDict):
    percent: float
    available_mb: float
    used_mb: float
    total_mb: float


class DiskResourcePayload(TypedDict):
    percent: float
    free_gb: float
    total_gb: float


class SystemResourcesPayload(TypedDict):
    cpu_percent: float
    memory: MemoryResourcePayload
    disk: DiskResourcePayload
    load_average: list[float] | None
    uptime_seconds: float


class DetailedSystemPayload(TypedDict):
    platform: str
    python_version: str
    cpu_count: int | None
    resources: SystemResourcesPayload


class DetailedHealthPayload(TypedDict):
    status: str
    timestamp: str
    version: str
    uptime_seconds: float
    components: dict[str, ComponentHealthPayload | ExternalApisPayload]
    system: DetailedSystemPayload
    error: NotRequired[str]


class BasicDatabaseHealthPayload(TypedDict):
    status: str
    healthy: bool
    response_time_ms: float


class BasicHealthPayload(TypedDict):
    status: str
    timestamp: str
    version: str
    uptime_seconds: float
    database: BasicDatabaseHealthPayload
    error: NotRequired[str]


class HealthStatus(Enum):
    """Health status levels for components and the aggregate system."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class ProbeResult:
    """Dependency-specific classification before timing metadata is attached."""

    status: HealthStatus
    message: str
    details: Mapping[str, Any]


@dataclass(frozen=True)
class HealthProbe:
    """A named dependency check and its status when the check raises."""

    name: str
    check: Callable[[], ProbeResult]
    failure_status: HealthStatus = HealthStatus.UNHEALTHY


@dataclass(frozen=True)
class ComponentHealth:
    """Timed health result for one registered component."""

    name: str
    status: HealthStatus
    message: str
    details: Mapping[str, Any]
    response_time_ms: float
    last_check: datetime

    def to_dict(self) -> ComponentHealthPayload:
        """Serialize the component once for every JSON consumer."""
        return {
            "status": self.status.value,
            "message": self.message,
            "response_time_ms": self.response_time_ms,
            "details": dict(self.details),
            "last_check": iso_z(self.last_check),
        }


@dataclass(frozen=True)
class SystemResources:
    """System resource utilization captured with a health snapshot."""

    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_free_gb: float
    disk_total_gb: float
    load_average: tuple[float, float, float] | None
    uptime_seconds: float

    def to_dict(self) -> SystemResourcesPayload:
        return {
            "cpu_percent": self.cpu_percent,
            "memory": {
                "percent": self.memory_percent,
                "available_mb": self.memory_available_mb,
                "used_mb": self.memory_used_mb,
                "total_mb": self.memory_total_mb,
            },
            "disk": {
                "percent": self.disk_percent,
                "free_gb": self.disk_free_gb,
                "total_gb": self.disk_total_gb,
            },
            "load_average": list(self.load_average) if self.load_average else None,
            "uptime_seconds": self.uptime_seconds,
        }


@dataclass(frozen=True)
class HealthSnapshot:
    """One policy-neutral observation shared by every detailed renderer."""

    checked_at: datetime
    version: str
    application_uptime_seconds: float
    components: Mapping[str, ComponentHealth]
    resources: SystemResources
    platform_name: str
    python_version: str
    cpu_count: int | None


_STATUS_PRIORITY = {
    HealthStatus.HEALTHY: 0,
    HealthStatus.UNKNOWN: 1,
    HealthStatus.DEGRADED: 2,
    HealthStatus.UNHEALTHY: 3,
    HealthStatus.CRITICAL: 4,
}


def overall_health_status(components: Mapping[str, ComponentHealth]) -> HealthStatus:
    """Reduce component statuses without coupling probes to endpoint policy."""
    if not components:
        return HealthStatus.UNKNOWN
    return max(
        (component.status for component in components.values()),
        key=_STATUS_PRIORITY.__getitem__,
    )


def iso_z(value: datetime) -> str:
    """Render a naive UTC datetime in the health payloads' ISO-with-Z shape."""
    return value.isoformat() + "Z"
