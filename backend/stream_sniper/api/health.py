"""
Comprehensive health check and system monitoring module for the Stream Sniper API.
Provides detailed health status, system metrics, and external dependency validation.
"""

import os
import time
import psutil
import platform
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import get_config
from .cache import get_cache
from .rate_limiter import get_rate_limit_stats
from ..database.connection_pool import get_pool

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status levels for components and overall system."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status for individual system components."""

    name: str
    status: HealthStatus
    message: str
    details: Dict[str, Any]
    response_time_ms: Optional[float] = None
    last_check: Optional[datetime] = None


@dataclass
class SystemResources:
    """System resource utilization metrics."""

    cpu_percent: float
    memory_percent: float
    memory_available_mb: float
    memory_used_mb: float
    memory_total_mb: float
    disk_percent: float
    disk_free_gb: float
    disk_total_gb: float
    load_average: Optional[List[float]]
    uptime_seconds: float


class HealthChecker:
    """
    Comprehensive health check service for monitoring system and dependencies.
    """

    def __init__(self):
        """Initialize health checker with configuration."""
        self.config = get_config()
        self.start_time = datetime.now()

        # External service timeouts
        self.request_timeout = 5.0
        self.max_retries = 2

        # Setup HTTP session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

    def check_database_health(self) -> ComponentHealth:
        """
        Check database connectivity and performance.

        Returns:
            ComponentHealth object with database status
        """
        start_time = time.time()

        try:
            pool = get_pool()

            # Get pool status
            pool_status = pool.get_pool_status()

            # Perform health check query
            is_healthy = pool.health_check()

            response_time = (time.time() - start_time) * 1000

            if is_healthy:
                status = HealthStatus.HEALTHY
                message = "Database connection pool is healthy"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Database health check failed"

            details = {**pool_status, "query_test": is_healthy, "response_time_ms": round(response_time, 2)}

            return ComponentHealth(
                name="database",
                status=status,
                message=message,
                details=details,
                response_time_ms=response_time,
                last_check=datetime.now(),
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Database health check failed: {e}")

            return ComponentHealth(
                name="database",
                status=HealthStatus.CRITICAL,
                message=f"Database connection failed: {str(e)}",
                details={"error": str(e), "response_time_ms": round(response_time, 2)},
                response_time_ms=response_time,
                last_check=datetime.now(),
            )

    def check_cache_health(self) -> ComponentHealth:
        """
        Check Redis cache connectivity and performance.

        Returns:
            ComponentHealth object with cache status
        """
        start_time = time.time()

        try:
            cache = get_cache()
            cache_stats = cache.get_stats()

            response_time = (time.time() - start_time) * 1000

            # Determine status based on cache stats
            if not cache.enabled:
                status = HealthStatus.DEGRADED
                message = "Cache is disabled"
            elif cache_stats.get("status") == "healthy":
                status = HealthStatus.HEALTHY
                message = "Cache is operational"
            elif cache_stats.get("status") == "unhealthy":
                status = HealthStatus.UNHEALTHY
                message = "Cache is unhealthy"
            else:
                status = HealthStatus.UNKNOWN
                message = "Cache status unknown"

            return ComponentHealth(
                name="cache",
                status=status,
                message=message,
                details=cache_stats,
                response_time_ms=response_time,
                last_check=datetime.now(),
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Cache health check failed: {e}")

            return ComponentHealth(
                name="cache",
                status=HealthStatus.UNHEALTHY,
                message=f"Cache check failed: {str(e)}",
                details={"error": str(e), "response_time_ms": round(response_time, 2)},
                response_time_ms=response_time,
                last_check=datetime.now(),
            )

    def check_rate_limiter_health(self) -> ComponentHealth:
        """
        Check rate limiter functionality.

        Returns:
            ComponentHealth object with rate limiter status
        """
        start_time = time.time()

        try:
            if not self.config.rate_limit.enabled:
                return ComponentHealth(
                    name="rate_limiter",
                    status=HealthStatus.DEGRADED,
                    message="Rate limiting is disabled",
                    details={"enabled": False},
                    response_time_ms=(time.time() - start_time) * 1000,
                    last_check=datetime.now(),
                )

            rate_limit_stats = get_rate_limit_stats()
            response_time = (time.time() - start_time) * 1000

            # Check if rate limiter is working
            if rate_limit_stats.get("enabled", False):
                status = HealthStatus.HEALTHY
                message = "Rate limiter is operational"
            else:
                status = HealthStatus.UNHEALTHY
                message = "Rate limiter is not functioning"

            return ComponentHealth(
                name="rate_limiter",
                status=status,
                message=message,
                details=rate_limit_stats,
                response_time_ms=response_time,
                last_check=datetime.now(),
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Rate limiter health check failed: {e}")

            return ComponentHealth(
                name="rate_limiter",
                status=HealthStatus.UNHEALTHY,
                message=f"Rate limiter check failed: {str(e)}",
                details={"error": str(e), "response_time_ms": round(response_time, 2)},
                response_time_ms=response_time,
                last_check=datetime.now(),
            )

    def check_twitch_api_health(self) -> ComponentHealth:
        """
        Check external Twitch API connectivity.

        Returns:
            ComponentHealth object with Twitch API status
        """
        start_time = time.time()

        try:
            # Test Twitch API endpoint (public, no auth required)
            url = "https://api.twitch.tv/helix/users"
            headers = {"Client-ID": os.getenv("TWITCH_CLIENT_ID", "test"), "User-Agent": "StreamSniper/1.0"}

            response = self.session.get(url, headers=headers, timeout=self.request_timeout)

            response_time = (time.time() - start_time) * 1000

            # Check response
            if response.status_code == 401:
                # 401 is expected without proper auth, but means API is responding
                status = HealthStatus.HEALTHY
                message = "Twitch API is reachable"
            elif response.status_code < 500:
                status = HealthStatus.HEALTHY
                message = "Twitch API is responding"
            else:
                status = HealthStatus.DEGRADED
                message = f"Twitch API returned {response.status_code}"

            details = {"status_code": response.status_code, "response_time_ms": round(response_time, 2), "url": url}

            return ComponentHealth(
                name="twitch_api",
                status=status,
                message=message,
                details=details,
                response_time_ms=response_time,
                last_check=datetime.now(),
            )

        except requests.exceptions.Timeout:
            response_time = (time.time() - start_time) * 1000
            return ComponentHealth(
                name="twitch_api",
                status=HealthStatus.DEGRADED,
                message="Twitch API timeout",
                details={"error": "timeout", "response_time_ms": round(response_time, 2)},
                response_time_ms=response_time,
                last_check=datetime.now(),
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            logger.error(f"Twitch API health check failed: {e}")

            return ComponentHealth(
                name="twitch_api",
                status=HealthStatus.UNHEALTHY,
                message=f"Twitch API check failed: {str(e)}",
                details={"error": str(e), "response_time_ms": round(response_time, 2)},
                response_time_ms=response_time,
                last_check=datetime.now(),
            )

    def get_system_resources(self) -> SystemResources:
        """
        Get current system resource utilization.

        Returns:
            SystemResources object with current metrics
        """
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)

            # Memory usage
            memory = psutil.virtual_memory()
            memory_mb = 1024 * 1024

            # Disk usage (for current working directory)
            disk = psutil.disk_usage("/")
            disk_gb = 1024 * 1024 * 1024

            # Load average (Unix systems only)
            load_avg = None
            try:
                if hasattr(os, "getloadavg"):
                    load_avg = list(os.getloadavg())
            except (OSError, AttributeError):
                pass

            # System uptime
            boot_time = psutil.boot_time()
            uptime_seconds = time.time() - boot_time

            return SystemResources(
                cpu_percent=round(cpu_percent, 1),
                memory_percent=round(memory.percent, 1),
                memory_available_mb=round(memory.available / memory_mb, 1),
                memory_used_mb=round(memory.used / memory_mb, 1),
                memory_total_mb=round(memory.total / memory_mb, 1),
                disk_percent=round(disk.used / disk.total * 100, 1),
                disk_free_gb=round(disk.free / disk_gb, 2),
                disk_total_gb=round(disk.total / disk_gb, 2),
                load_average=load_avg,
                uptime_seconds=round(uptime_seconds, 0),
            )

        except Exception as e:
            logger.error(f"Failed to get system resources: {e}")
            # Return default values if we can't get system info
            return SystemResources(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_available_mb=0.0,
                memory_used_mb=0.0,
                memory_total_mb=0.0,
                disk_percent=0.0,
                disk_free_gb=0.0,
                disk_total_gb=0.0,
                load_average=None,
                uptime_seconds=0.0,
            )

    def get_basic_health(self) -> Tuple[HealthStatus, Dict[str, Any]]:
        """
        Get basic health status for load balancer health checks.
        Only checks critical components (database).

        Returns:
            Tuple of (overall_status, health_data)
        """
        db_health = self.check_database_health()

        # For basic health check, only database needs to be healthy
        overall_status = db_health.status

        health_data = {
            "status": overall_status.value,
            "timestamp": datetime.now().isoformat() + "Z",
            "version": self.config.version,
            "uptime_seconds": round((datetime.now() - self.start_time).total_seconds(), 0),
            "database": {
                "status": db_health.status.value,
                "healthy": db_health.status == HealthStatus.HEALTHY,
                "response_time_ms": db_health.response_time_ms,
            },
        }

        return overall_status, health_data

    def get_detailed_health(self) -> Tuple[HealthStatus, Dict[str, Any]]:
        """
        Get comprehensive health status with all component checks.

        Returns:
            Tuple of (overall_status, detailed_health_data)
        """
        # Check all components
        db_health = self.check_database_health()
        cache_health = self.check_cache_health()
        rate_limit_health = self.check_rate_limiter_health()
        twitch_health = self.check_twitch_api_health()

        # Get system resources
        system_resources = self.get_system_resources()

        # Determine overall status
        component_statuses = [db_health.status, cache_health.status, rate_limit_health.status, twitch_health.status]

        # Priority: CRITICAL > UNHEALTHY > DEGRADED > HEALTHY
        if HealthStatus.CRITICAL in component_statuses:
            overall_status = HealthStatus.CRITICAL
        elif HealthStatus.UNHEALTHY in component_statuses:
            overall_status = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in component_statuses:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        # Build detailed response
        health_data = {
            "status": overall_status.value,
            "timestamp": datetime.now().isoformat() + "Z",
            "version": self.config.version,
            "uptime_seconds": round((datetime.now() - self.start_time).total_seconds(), 0),
            "components": {
                "database": {
                    "status": db_health.status.value,
                    "message": db_health.message,
                    "response_time_ms": db_health.response_time_ms,
                    "details": db_health.details,
                    "last_check": db_health.last_check.isoformat() + "Z" if db_health.last_check else None,
                },
                "cache": {
                    "status": cache_health.status.value,
                    "message": cache_health.message,
                    "response_time_ms": cache_health.response_time_ms,
                    "details": cache_health.details,
                    "last_check": cache_health.last_check.isoformat() + "Z" if cache_health.last_check else None,
                },
                "rate_limiter": {
                    "status": rate_limit_health.status.value,
                    "message": rate_limit_health.message,
                    "response_time_ms": rate_limit_health.response_time_ms,
                    "details": rate_limit_health.details,
                    "last_check": (
                        rate_limit_health.last_check.isoformat() + "Z" if rate_limit_health.last_check else None
                    ),
                },
                "external_apis": {
                    "twitch": {
                        "status": twitch_health.status.value,
                        "message": twitch_health.message,
                        "response_time_ms": twitch_health.response_time_ms,
                        "details": twitch_health.details,
                        "last_check": twitch_health.last_check.isoformat() + "Z" if twitch_health.last_check else None,
                    }
                },
            },
            "system": {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "cpu_count": os.cpu_count(),
                "resources": {
                    "cpu_percent": system_resources.cpu_percent,
                    "memory": {
                        "percent": system_resources.memory_percent,
                        "available_mb": system_resources.memory_available_mb,
                        "used_mb": system_resources.memory_used_mb,
                        "total_mb": system_resources.memory_total_mb,
                    },
                    "disk": {
                        "percent": system_resources.disk_percent,
                        "free_gb": system_resources.disk_free_gb,
                        "total_gb": system_resources.disk_total_gb,
                    },
                    "load_average": system_resources.load_average,
                    "uptime_seconds": system_resources.uptime_seconds,
                },
            },
        }

        return overall_status, health_data

    def generate_prometheus_metrics(self) -> str:
        """
        Generate Prometheus-compatible metrics.

        Returns:
            String containing Prometheus metrics format
        """
        try:
            # Get health status for all components
            db_health = self.check_database_health()
            cache_health = self.check_cache_health()
            rate_limit_health = self.check_rate_limiter_health()
            twitch_health = self.check_twitch_api_health()
            system_resources = self.get_system_resources()

            # Convert health status to numeric values
            status_values = {
                HealthStatus.HEALTHY: 1,
                HealthStatus.DEGRADED: 0.75,
                HealthStatus.UNHEALTHY: 0.5,
                HealthStatus.CRITICAL: 0,
                HealthStatus.UNKNOWN: -1,
            }

            current_time = int(time.time() * 1000)  # Prometheus expects milliseconds

            metrics = [
                "# HELP stream_sniper_component_health Health status of system components (1=healthy, 0.75=degraded, 0.5=unhealthy, 0=critical)",
                "# TYPE stream_sniper_component_health gauge",
                f'stream_sniper_component_health{{component="database"}} {status_values[db_health.status]} {current_time}',
                f'stream_sniper_component_health{{component="cache"}} {status_values[cache_health.status]} {current_time}',
                f'stream_sniper_component_health{{component="rate_limiter"}} {status_values[rate_limit_health.status]} {current_time}',
                f'stream_sniper_component_health{{component="twitch_api"}} {status_values[twitch_health.status]} {current_time}',
                "",
                "# HELP stream_sniper_component_response_time_ms Response time of component health checks in milliseconds",
                "# TYPE stream_sniper_component_response_time_ms gauge",
                f'stream_sniper_component_response_time_ms{{component="database"}} {db_health.response_time_ms or 0} {current_time}',
                f'stream_sniper_component_response_time_ms{{component="cache"}} {cache_health.response_time_ms or 0} {current_time}',
                f'stream_sniper_component_response_time_ms{{component="rate_limiter"}} {rate_limit_health.response_time_ms or 0} {current_time}',
                f'stream_sniper_component_response_time_ms{{component="twitch_api"}} {twitch_health.response_time_ms or 0} {current_time}',
                "",
                "# HELP stream_sniper_system_cpu_percent Current CPU usage percentage",
                "# TYPE stream_sniper_system_cpu_percent gauge",
                f"stream_sniper_system_cpu_percent {system_resources.cpu_percent} {current_time}",
                "",
                "# HELP stream_sniper_system_memory_percent Current memory usage percentage",
                "# TYPE stream_sniper_system_memory_percent gauge",
                f"stream_sniper_system_memory_percent {system_resources.memory_percent} {current_time}",
                "",
                "# HELP stream_sniper_system_memory_mb Memory usage in megabytes",
                "# TYPE stream_sniper_system_memory_mb gauge",
                f'stream_sniper_system_memory_mb{{type="available"}} {system_resources.memory_available_mb} {current_time}',
                f'stream_sniper_system_memory_mb{{type="used"}} {system_resources.memory_used_mb} {current_time}',
                f'stream_sniper_system_memory_mb{{type="total"}} {system_resources.memory_total_mb} {current_time}',
                "",
                "# HELP stream_sniper_system_disk_percent Current disk usage percentage",
                "# TYPE stream_sniper_system_disk_percent gauge",
                f"stream_sniper_system_disk_percent {system_resources.disk_percent} {current_time}",
                "",
                "# HELP stream_sniper_system_disk_gb Disk usage in gigabytes",
                "# TYPE stream_sniper_system_disk_gb gauge",
                f'stream_sniper_system_disk_gb{{type="free"}} {system_resources.disk_free_gb} {current_time}',
                f'stream_sniper_system_disk_gb{{type="total"}} {system_resources.disk_total_gb} {current_time}',
                "",
                "# HELP stream_sniper_uptime_seconds Application uptime in seconds",
                "# TYPE stream_sniper_uptime_seconds counter",
                f"stream_sniper_uptime_seconds {round((datetime.now() - self.start_time).total_seconds(), 0)} {current_time}",
            ]

            # Add load average if available
            if system_resources.load_average:
                metrics.extend(
                    [
                        "",
                        "# HELP stream_sniper_system_load_average System load average",
                        "# TYPE stream_sniper_system_load_average gauge",
                        f'stream_sniper_system_load_average{{period="1m"}} {system_resources.load_average[0]} {current_time}',
                        f'stream_sniper_system_load_average{{period="5m"}} {system_resources.load_average[1]} {current_time}',
                        f'stream_sniper_system_load_average{{period="15m"}} {system_resources.load_average[2]} {current_time}',
                    ]
                )

            return "\n".join(metrics) + "\n"

        except Exception as e:
            logger.error(f"Failed to generate Prometheus metrics: {e}")
            error_time = int(time.time() * 1000)
            return f"""# HELP stream_sniper_metrics_error Error generating metrics
# TYPE stream_sniper_metrics_error gauge
stream_sniper_metrics_error 1 {error_time}
"""


# Global health checker instance
_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """
    Get the global health checker instance.

    Returns:
        HealthChecker instance
    """
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker
