"""Dependency probes, health snapshots, and monitoring renderers."""

import logging
import os
import platform
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, NotRequired, TypedDict

import psutil  # type: ignore[import-untyped]
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ...database.core.connection_pool import get_active_pool
from ..caching.cache import InProcessCache
from ..config import APIConfig
from ..security.rate_limiter import get_rate_limit_stats

logger = logging.getLogger(__name__)
MILLISECONDS_PER_SECOND = 1_000
BYTES_PER_MEBIBYTE = 1_024 * 1_024
BYTES_PER_GIBIBYTE = 1_024**3
TWITCH_USERS_API_URL = "https://api.twitch.tv/helix/users"


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
            "last_check": _iso_z(self.last_check),
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

_PROMETHEUS_STATUS = {
    HealthStatus.HEALTHY: 1,
    HealthStatus.DEGRADED: 0.75,
    HealthStatus.UNHEALTHY: 0.5,
    HealthStatus.CRITICAL: 0,
    HealthStatus.UNKNOWN: -1,
}


def overall_health_status(components: Mapping[str, ComponentHealth]) -> HealthStatus:
    """Reduce component statuses without coupling probes to endpoint policy."""
    if not components:
        return HealthStatus.UNKNOWN
    return max(
        (component.status for component in components.values()),
        key=_STATUS_PRIORITY.__getitem__,
    )


def detailed_health_payload(snapshot: HealthSnapshot) -> DetailedHealthPayload:
    """Render the detailed JSON contract from an already-collected snapshot."""
    component_payloads = {name: component.to_dict() for name, component in snapshot.components.items()}
    twitch = component_payloads.pop("twitch_api", None)
    serialized: dict[str, ComponentHealthPayload | ExternalApisPayload] = dict(component_payloads)
    if twitch is not None:
        serialized["external_apis"] = {"twitch": twitch}
    return {
        "status": overall_health_status(snapshot.components).value,
        "timestamp": _iso_z(snapshot.checked_at),
        "version": snapshot.version,
        "uptime_seconds": snapshot.application_uptime_seconds,
        "components": serialized,
        "system": {
            "platform": snapshot.platform_name,
            "python_version": snapshot.python_version,
            "cpu_count": snapshot.cpu_count,
            "resources": snapshot.resources.to_dict(),
        },
    }


def render_prometheus(snapshot: HealthSnapshot) -> str:
    """Render one snapshot in Prometheus text exposition format."""
    timestamp_ms = int(snapshot.checked_at.timestamp() * MILLISECONDS_PER_SECOND)
    lines = [
        "# HELP stream_sniper_component_health Health status of system components",
        "# TYPE stream_sniper_component_health gauge",
    ]
    for name, component in snapshot.components.items():
        lines.append(
            f'stream_sniper_component_health{{component="{name}"}} '
            f"{_PROMETHEUS_STATUS[component.status]} {timestamp_ms}"
        )
    lines.extend(
        [
            "",
            "# HELP stream_sniper_component_response_time_ms Component health-check duration",
            "# TYPE stream_sniper_component_response_time_ms gauge",
        ]
    )
    for name, component in snapshot.components.items():
        lines.append(
            f'stream_sniper_component_response_time_ms{{component="{name}"}} '
            f"{component.response_time_ms} {timestamp_ms}"
        )
    resources = snapshot.resources
    lines.extend(
        [
            "",
            "# HELP stream_sniper_system_cpu_percent Current CPU usage percentage",
            "# TYPE stream_sniper_system_cpu_percent gauge",
            f"stream_sniper_system_cpu_percent {resources.cpu_percent} {timestamp_ms}",
            "",
            "# HELP stream_sniper_system_memory_percent Current memory usage percentage",
            "# TYPE stream_sniper_system_memory_percent gauge",
            f"stream_sniper_system_memory_percent {resources.memory_percent} {timestamp_ms}",
            "",
            "# HELP stream_sniper_system_memory_mb Memory usage in megabytes",
            "# TYPE stream_sniper_system_memory_mb gauge",
            f'stream_sniper_system_memory_mb{{type="available"}} {resources.memory_available_mb} {timestamp_ms}',
            f'stream_sniper_system_memory_mb{{type="used"}} {resources.memory_used_mb} {timestamp_ms}',
            f'stream_sniper_system_memory_mb{{type="total"}} {resources.memory_total_mb} {timestamp_ms}',
            "",
            "# HELP stream_sniper_system_disk_percent Current disk usage percentage",
            "# TYPE stream_sniper_system_disk_percent gauge",
            f"stream_sniper_system_disk_percent {resources.disk_percent} {timestamp_ms}",
            "",
            "# HELP stream_sniper_system_disk_gb Disk usage in gigabytes",
            "# TYPE stream_sniper_system_disk_gb gauge",
            f'stream_sniper_system_disk_gb{{type="free"}} {resources.disk_free_gb} {timestamp_ms}',
            f'stream_sniper_system_disk_gb{{type="total"}} {resources.disk_total_gb} {timestamp_ms}',
            "",
            "# HELP stream_sniper_uptime_seconds Application uptime in seconds",
            "# TYPE stream_sniper_uptime_seconds gauge",
            f"stream_sniper_uptime_seconds {snapshot.application_uptime_seconds} {timestamp_ms}",
        ]
    )
    if resources.load_average is not None:
        lines.extend(
            [
                "",
                "# HELP stream_sniper_system_load_average System load average",
                "# TYPE stream_sniper_system_load_average gauge",
                f'stream_sniper_system_load_average{{period="1m"}} {resources.load_average[0]} {timestamp_ms}',
                f'stream_sniper_system_load_average{{period="5m"}} {resources.load_average[1]} {timestamp_ms}',
                f'stream_sniper_system_load_average{{period="15m"}} {resources.load_average[2]} {timestamp_ms}',
            ]
        )
    return "\n".join(lines) + "\n"


class HealthChecker:
    """Collect dependency probes and resources into one health snapshot."""

    def __init__(
        self,
        *,
        config: APIConfig,
        cache: InProcessCache,
        session: requests.Session | None = None,
        probes: Sequence[HealthProbe] | None = None,
        resource_reader: Callable[[], SystemResources] | None = None,
        monotonic: Callable[[], float] = time.perf_counter,
        now: Callable[[], datetime] = datetime.now,
    ) -> None:
        self.config = config
        self.cache = cache
        self._now = now
        self._monotonic = monotonic
        self.start_time = now()
        self.request_timeout = 5.0
        self.session = session or self._build_session()
        self._owns_session = session is None
        self._resource_reader = resource_reader or self.get_system_resources
        registered = probes if probes is not None else self._default_probes()
        self.probes = {probe.name: probe for probe in registered}

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        adapter = HTTPAdapter(
            max_retries=Retry(
                total=2,
                backoff_factor=0.5,
                status_forcelist=[429, 500, 502, 503, 504],
            )
        )
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session

    def _default_probes(self) -> tuple[HealthProbe, ...]:
        return (
            HealthProbe("database", self._probe_database, HealthStatus.CRITICAL),
            HealthProbe("cache", self._probe_cache),
            HealthProbe("rate_limiter", self._probe_rate_limiter),
            HealthProbe("twitch_api", self._probe_twitch_api),
        )

    def close(self) -> None:
        """Close only an HTTP session created and owned by this checker."""
        if self._owns_session:
            self.session.close()

    def _run_probe(self, probe: HealthProbe) -> ComponentHealth:
        started = self._monotonic()
        try:
            result = probe.check()
        except Exception as exc:
            logger.warning("%s health probe failed: %s", probe.name, exc)
            result = ProbeResult(
                status=probe.failure_status,
                message=f"{probe.name.replace('_', ' ').title()} check failed",
                details={"error": str(exc)},
            )
        duration_ms = round(
            (self._monotonic() - started) * MILLISECONDS_PER_SECOND,
            2,
        )
        return ComponentHealth(
            name=probe.name,
            status=result.status,
            message=result.message,
            details=result.details,
            response_time_ms=duration_ms,
            last_check=self._now(),
        )

    def snapshot(self) -> HealthSnapshot:
        """Execute every registered probe exactly once and sample resources once."""
        components = {name: self._run_probe(probe) for name, probe in self.probes.items()}
        checked_at = self._now()
        return HealthSnapshot(
            checked_at=checked_at,
            version=self.config.version,
            application_uptime_seconds=round((checked_at - self.start_time).total_seconds(), 0),
            components=components,
            resources=self._resource_reader(),
            platform_name=platform.platform(),
            python_version=platform.python_version(),
            cpu_count=os.cpu_count(),
        )

    def _probe_database(self) -> ProbeResult:
        pool = get_active_pool()
        pool_status = pool.get_pool_status()
        healthy = pool.health_check()
        return ProbeResult(
            status=HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY,
            message=("Database connection pool is healthy" if healthy else "Database health check failed"),
            details={**pool_status, "query_test": healthy},
        )

    def _probe_cache(self) -> ProbeResult:
        stats = self.cache.get_stats()
        if not self.cache.enabled:
            status, message = HealthStatus.DEGRADED, "Cache is disabled"
        elif stats["status"] == "healthy":
            status, message = HealthStatus.HEALTHY, "Cache is operational"
        elif stats["status"] == "unhealthy":
            status, message = HealthStatus.UNHEALTHY, "Cache is unhealthy"
        else:
            status, message = HealthStatus.UNKNOWN, "Cache status unknown"
        return ProbeResult(status, message, stats)

    def _probe_rate_limiter(self) -> ProbeResult:
        if not self.config.rate_limit.enabled:
            return ProbeResult(
                HealthStatus.DEGRADED,
                "Rate limiting is disabled",
                {"enabled": False},
            )
        stats = get_rate_limit_stats(self.config.rate_limit)
        healthy = stats["enabled"]
        return ProbeResult(
            HealthStatus.HEALTHY if healthy else HealthStatus.UNHEALTHY,
            "Rate limiter is operational" if healthy else "Rate limiter is not functioning",
            stats,
        )

    def _probe_twitch_api(self) -> ProbeResult:
        url = TWITCH_USERS_API_URL
        headers = {
            "Client-ID": os.getenv("TWITCH_CLIENT_ID", "test"),
            "User-Agent": "StreamSniper/1.0",
        }
        try:
            response = self.session.get(url, headers=headers, timeout=self.request_timeout)
        except requests.exceptions.Timeout:
            return ProbeResult(
                HealthStatus.DEGRADED,
                "Twitch API timeout",
                {"error": "timeout", "url": url},
            )
        if response.status_code < 500:
            status = HealthStatus.HEALTHY
            message = "Twitch API is reachable"
        else:
            status = HealthStatus.DEGRADED
            message = f"Twitch API returned {response.status_code}"
        return ProbeResult(status, message, {"status_code": response.status_code, "url": url})

    def get_system_resources(self) -> SystemResources:
        """Read process-independent resource metrics without blocking the request."""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            load_average = None
            if hasattr(os, "getloadavg"):
                load = os.getloadavg()
                load_average = (float(load[0]), float(load[1]), float(load[2]))
            return SystemResources(
                cpu_percent=round(psutil.cpu_percent(interval=None), 1),
                memory_percent=round(memory.percent, 1),
                memory_available_mb=round(memory.available / BYTES_PER_MEBIBYTE, 1),
                memory_used_mb=round(memory.used / BYTES_PER_MEBIBYTE, 1),
                memory_total_mb=round(memory.total / BYTES_PER_MEBIBYTE, 1),
                disk_percent=round(disk.used / disk.total * 100, 1),
                disk_free_gb=round(disk.free / BYTES_PER_GIBIBYTE, 2),
                disk_total_gb=round(disk.total / BYTES_PER_GIBIBYTE, 2),
                load_average=load_average,
                uptime_seconds=round(time.time() - psutil.boot_time(), 0),
            )
        except Exception as exc:
            logger.warning("Failed to read system resources: %s", exc)
            return SystemResources(0, 0, 0, 0, 0, 0, 0, 0, None, 0)

    def get_basic_health(self) -> tuple[HealthStatus, BasicHealthPayload]:
        database = self._run_probe(self.probes["database"])
        checked_at = self._now()
        return database.status, {
            "status": database.status.value,
            "timestamp": _iso_z(checked_at),
            "version": self.config.version,
            "uptime_seconds": round((checked_at - self.start_time).total_seconds(), 0),
            "database": {
                "status": database.status.value,
                "healthy": database.status == HealthStatus.HEALTHY,
                "response_time_ms": database.response_time_ms,
            },
        }

    def get_detailed_health(self) -> tuple[HealthStatus, DetailedHealthPayload]:
        snapshot = self.snapshot()
        return overall_health_status(snapshot.components), detailed_health_payload(snapshot)

    def generate_prometheus_metrics(self) -> str:
        try:
            return render_prometheus(self.snapshot())
        except Exception as exc:
            logger.warning("Failed to generate Prometheus metrics: %s", exc)
            error_time = int(time.time() * MILLISECONDS_PER_SECOND)
            return (
                "# HELP stream_sniper_metrics_error Error generating metrics\n"
                "# TYPE stream_sniper_metrics_error gauge\n"
                f"stream_sniper_metrics_error 1 {error_time}\n"
            )


def _iso_z(value: datetime) -> str:
    return value.isoformat() + "Z"
