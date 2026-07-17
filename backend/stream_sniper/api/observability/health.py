"""Dependency probing: collect health snapshots from live system dependencies.

Contracts live in ``health_contracts``; JSON/Prometheus rendering lives in
``health_renderers``. This module owns the I/O: database, cache, rate-limiter,
and Twitch probes plus system-resource sampling.
"""

import logging
import os
import platform
import time
from collections.abc import Callable, Sequence
from datetime import datetime

import psutil  # type: ignore[import-untyped]
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ...database.core.connection_pool import get_active_pool
from ..caching.cache import InProcessCache
from ..config import APIConfig
from ..security.rate_limiter import get_rate_limit_stats
from .health_contracts import (
    BasicHealthPayload,
    ComponentHealth,
    DetailedHealthPayload,
    HealthProbe,
    HealthSnapshot,
    HealthStatus,
    ProbeResult,
    SystemResources,
    iso_z,
    overall_health_status,
)
from .health_renderers import (
    MILLISECONDS_PER_SECOND,
    detailed_health_payload,
    render_prometheus,
)

logger = logging.getLogger(__name__)
BYTES_PER_MEBIBYTE = 1_024 * 1_024
BYTES_PER_GIBIBYTE = 1_024**3
TWITCH_USERS_API_URL = "https://api.twitch.tv/helix/users"


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
            "Client-ID": self.config.twitch_client_id or "test",
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
            "timestamp": iso_z(checked_at),
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
