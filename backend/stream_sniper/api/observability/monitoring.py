"""Thread-safe in-memory API metrics with bounded request-history retention."""

import logging
from collections import defaultdict, deque
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Lock
from typing import Literal, TypedDict

logger = logging.getLogger(__name__)

CacheOperation = Literal["hit", "miss", "set", "delete", "error"]


class MetricsSystemPayload(TypedDict):
    uptime_seconds: float
    start_time: str
    last_cleanup: str


class RequestSnapshotPayload(TypedDict):
    total: int
    per_minute: float
    avg_response_time_ms: float
    status_codes: dict[str, int]


class CacheOperationsPayload(TypedDict):
    hits: int
    misses: int
    sets: int
    deletes: int
    errors: int


class CachePrefixPayload(TypedDict):
    hit_rate: float
    operations: CacheOperationsPayload


class CacheSnapshotPayload(TypedDict):
    hit_rate: float
    miss_rate: float
    total_operations: CacheOperationsPayload
    by_prefix: dict[str, CachePrefixPayload]


class RateLimitSnapshotPayload(TypedDict):
    total_requests: int
    rate_limited_requests: int
    rate_limit_percentage: float
    endpoint_hits: dict[str, int]


class EndpointSnapshotPayload(TypedDict):
    count: int
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    error_rate: float
    cache_hit_rate: float


class EndpointAccumulator(TypedDict):
    count: int
    total_response_time: float
    min_response_time: float
    max_response_time: float
    error_count: int
    cache_hits: int
    rate_limited: int


class RecentRequestPayload(TypedDict):
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    timestamp: str
    client_ip: str
    cache_hit: bool
    rate_limited: bool


class MonitoringSnapshotPayload(TypedDict):
    system: MetricsSystemPayload
    requests: RequestSnapshotPayload
    cache: CacheSnapshotPayload
    rate_limiting: RateLimitSnapshotPayload
    endpoints: dict[str, EndpointSnapshotPayload]


@dataclass
class RequestMetrics:
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    timestamp: datetime
    client_ip: str
    user_agent: str | None = None
    cache_hit: bool = False
    rate_limited: bool = False


@dataclass
class CacheMetrics:
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    total_requests: int = 0

    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100

    @property
    def miss_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.misses / self.total_requests) * 100


@dataclass
class RateLimitMetrics:
    total_requests: int = 0
    rate_limited_requests: int = 0

    endpoint_hits: dict[str, int] = field(default_factory=dict)

    @property
    def rate_limit_percentage(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return (self.rate_limited_requests / self.total_requests) * 100


class MetricsCollector:
    def __init__(self, retention_hours: int = 24, max_request_history: int = 10000):
        self.retention_hours = retention_hours
        self.max_request_history = max_request_history
        self._lock = Lock()
        self.request_history: deque[RequestMetrics] = deque(maxlen=max_request_history)
        self.endpoint_stats: dict[str, EndpointAccumulator] = defaultdict(
            lambda: {
                "count": 0,
                "total_response_time": 0.0,
                "min_response_time": float("inf"),
                "max_response_time": 0.0,
                "error_count": 0,
                "cache_hits": 0,
                "rate_limited": 0,
            }
        )

        self.cache_metrics = CacheMetrics()
        self.cache_stats_by_prefix: dict[str, CacheMetrics] = defaultdict(CacheMetrics)
        self.rate_limit_metrics = RateLimitMetrics()
        self.start_time = datetime.now()
        self.last_cleanup = datetime.now()

    def record_request(self, metrics: RequestMetrics) -> None:
        with self._lock:
            self.request_history.append(metrics)
            endpoint_key = f"{metrics.method} {metrics.endpoint}"
            stats = self.endpoint_stats[endpoint_key]

            stats["count"] += 1
            stats["total_response_time"] += metrics.response_time_ms
            stats["min_response_time"] = min(stats["min_response_time"], metrics.response_time_ms)
            stats["max_response_time"] = max(stats["max_response_time"], metrics.response_time_ms)

            if metrics.status_code >= 400:
                stats["error_count"] += 1

            if metrics.cache_hit:
                stats["cache_hits"] += 1

            if metrics.rate_limited:
                stats["rate_limited"] += 1
            self.rate_limit_metrics.total_requests += 1
            if metrics.rate_limited:
                self.rate_limit_metrics.rate_limited_requests += 1
                self.rate_limit_metrics.endpoint_hits[metrics.endpoint] = (
                    self.rate_limit_metrics.endpoint_hits.get(metrics.endpoint, 0) + 1
                )

    def record_cache_hit(self, cache_key_prefix: str = "") -> None:
        with self._lock:
            self.cache_metrics.hits += 1
            self.cache_metrics.total_requests += 1

            if cache_key_prefix:
                self.cache_stats_by_prefix[cache_key_prefix].hits += 1
                self.cache_stats_by_prefix[cache_key_prefix].total_requests += 1

    def record_cache_miss(self, cache_key_prefix: str = "") -> None:
        with self._lock:
            self.cache_metrics.misses += 1
            self.cache_metrics.total_requests += 1

            if cache_key_prefix:
                self.cache_stats_by_prefix[cache_key_prefix].misses += 1
                self.cache_stats_by_prefix[cache_key_prefix].total_requests += 1

    def record_cache_set(self, cache_key_prefix: str = "") -> None:
        with self._lock:
            self.cache_metrics.sets += 1

            if cache_key_prefix:
                self.cache_stats_by_prefix[cache_key_prefix].sets += 1

    def record_cache_delete(self, cache_key_prefix: str = "") -> None:
        with self._lock:
            self.cache_metrics.deletes += 1

            if cache_key_prefix:
                self.cache_stats_by_prefix[cache_key_prefix].deletes += 1

    def record_cache_error(self, cache_key_prefix: str = "") -> None:
        with self._lock:
            self.cache_metrics.errors += 1

            if cache_key_prefix:
                self.cache_stats_by_prefix[cache_key_prefix].errors += 1

    def prune_and_summarize_metrics(self) -> MonitoringSnapshotPayload:
        with self._lock:
            self._cleanup_old_data()
            now = datetime.now()
            uptime_seconds = (now - self.start_time).total_seconds()
            top_endpoints = sorted(self.endpoint_stats.items(), key=lambda x: x[1]["count"], reverse=True)[:10]

            return {
                "system": {
                    "uptime_seconds": uptime_seconds,
                    "start_time": self.start_time.isoformat(),
                    "last_cleanup": self.last_cleanup.isoformat(),
                },
                "requests": self._request_snapshot(uptime_seconds),
                "cache": self._cache_snapshot(),
                "rate_limiting": {
                    "total_requests": self.rate_limit_metrics.total_requests,
                    "rate_limited_requests": self.rate_limit_metrics.rate_limited_requests,
                    "rate_limit_percentage": round(self.rate_limit_metrics.rate_limit_percentage, 2),
                    "endpoint_hits": dict(self.rate_limit_metrics.endpoint_hits),
                },
                "endpoints": self._endpoint_snapshot(top_endpoints),
            }

    def _request_snapshot(self, uptime_seconds: float) -> RequestSnapshotPayload:
        total_requests = len(self.request_history)
        requests_per_minute = (total_requests / uptime_seconds) * 60 if uptime_seconds > 0 else 0.0
        response_times = [request.response_time_ms for request in self.request_history]
        status_codes: dict[str, int] = defaultdict(int)
        for request in self.request_history:
            status_codes[str(request.status_code)] += 1
        return {
            "total": total_requests,
            "per_minute": round(requests_per_minute, 2),
            "avg_response_time_ms": round(sum(response_times) / len(response_times), 2) if response_times else 0,
            "status_codes": dict(status_codes),
        }

    def _cache_snapshot(self) -> CacheSnapshotPayload:
        def operations(metrics: CacheMetrics) -> CacheOperationsPayload:
            return {
                "hits": metrics.hits,
                "misses": metrics.misses,
                "sets": metrics.sets,
                "deletes": metrics.deletes,
                "errors": metrics.errors,
            }

        return {
            "hit_rate": round(self.cache_metrics.hit_rate, 2),
            "miss_rate": round(self.cache_metrics.miss_rate, 2),
            "total_operations": operations(self.cache_metrics),
            "by_prefix": {
                prefix: {"hit_rate": round(metrics.hit_rate, 2), "operations": operations(metrics)}
                for prefix, metrics in self.cache_stats_by_prefix.items()
            },
        }

    @staticmethod
    def _endpoint_snapshot(
        top_endpoints: list[tuple[str, EndpointAccumulator]],
    ) -> dict[str, EndpointSnapshotPayload]:
        return {
            endpoint: {
                "count": stats["count"],
                "avg_response_time_ms": round(stats["total_response_time"] / max(stats["count"], 1), 2),
                "min_response_time_ms": (
                    stats["min_response_time"] if stats["min_response_time"] != float("inf") else 0
                ),
                "max_response_time_ms": stats["max_response_time"],
                "error_rate": round((stats["error_count"] / max(stats["count"], 1)) * 100, 2),
                "cache_hit_rate": round((stats["cache_hits"] / max(stats["count"], 1)) * 100, 2),
            }
            for endpoint, stats in top_endpoints
        }

    def get_recent_requests(self, minutes: int = 10) -> list[RecentRequestPayload]:
        cutoff_time = datetime.now() - timedelta(minutes=minutes)

        with self._lock:
            recent_requests: list[RecentRequestPayload] = [
                {
                    "endpoint": req.endpoint,
                    "method": req.method,
                    "status_code": req.status_code,
                    "response_time_ms": req.response_time_ms,
                    "timestamp": req.timestamp.isoformat(),
                    "client_ip": req.client_ip,
                    "cache_hit": req.cache_hit,
                    "rate_limited": req.rate_limited,
                }
                for req in self.request_history
                if req.timestamp >= cutoff_time
            ]

        return recent_requests

    def reset_metrics(self) -> None:
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self.request_history.clear()
            self.endpoint_stats.clear()
            self.cache_metrics = CacheMetrics()
            self.cache_stats_by_prefix.clear()
            self.rate_limit_metrics = RateLimitMetrics()
            self.start_time = datetime.now()
            self.last_cleanup = datetime.now()

    def _cleanup_old_data(self) -> None:
        """Remove data older than the retention period."""
        now = datetime.now()
        cutoff_time = now - timedelta(hours=self.retention_hours)

        while self.request_history and self.request_history[0].timestamp < cutoff_time:
            self.request_history.popleft()

        self.last_cleanup = now


_request_metrics: ContextVar[MetricsCollector | None] = ContextVar("request_metrics", default=None)


def enter_metrics_scope(collector: MetricsCollector) -> Token[MetricsCollector | None]:
    """Bind one application's collector for request-local convenience calls."""
    return _request_metrics.set(collector)


def exit_metrics_scope(token: Token[MetricsCollector | None]) -> None:
    """Restore the previous request-local metrics binding."""
    _request_metrics.reset(token)


def _scoped_collector() -> MetricsCollector | None:
    return _request_metrics.get()


def record_request_metrics(collector: MetricsCollector, metrics: RequestMetrics) -> None:
    """Record a fully formed request event."""
    collector.record_request(metrics)


def record_cache_operation(operation: CacheOperation, cache_key_prefix: str = "") -> None:
    """Convenience function to record cache operations."""
    collector = _scoped_collector()
    if collector is None:
        return

    if operation == "hit":
        collector.record_cache_hit(cache_key_prefix)
    elif operation == "miss":
        collector.record_cache_miss(cache_key_prefix)
    elif operation == "set":
        collector.record_cache_set(cache_key_prefix)
    elif operation == "delete":
        collector.record_cache_delete(cache_key_prefix)
    elif operation == "error":
        collector.record_cache_error(cache_key_prefix)
    else:
        raise ValueError(f"Unsupported cache operation: {operation}")


def collect_monitoring_snapshot(collector: MetricsCollector) -> MonitoringSnapshotPayload:
    return collector.prune_and_summarize_metrics()
