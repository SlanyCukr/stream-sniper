"""
Monitoring and metrics collection for API performance, cache hits/misses, and rate limiting.
Provides comprehensive insights into system performance and usage patterns.
"""
import time
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock
import json

logger = logging.getLogger(__name__)


@dataclass
class RequestMetrics:
    """Metrics for individual API requests."""
    
    endpoint: str
    method: str
    status_code: int
    response_time_ms: float
    timestamp: datetime
    client_ip: str
    user_agent: Optional[str] = None
    cache_hit: bool = False
    rate_limited: bool = False


@dataclass
class CacheMetrics:
    """Cache performance metrics."""
    
    hits: int = 0
    misses: int = 0
    sets: int = 0
    deletes: int = 0
    errors: int = 0
    total_requests: int = 0
    
    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.hits / self.total_requests) * 100
    
    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate as percentage."""
        return 100.0 - self.hit_rate


@dataclass
class RateLimitMetrics:
    """Rate limiting metrics."""
    
    total_requests: int = 0
    rate_limited_requests: int = 0
    bypassed_requests: int = 0
    
    # Per-endpoint tracking
    endpoint_limits: Dict[str, int] = field(default_factory=dict)
    endpoint_hits: Dict[str, int] = field(default_factory=dict)
    
    @property
    def rate_limit_percentage(self) -> float:
        """Calculate percentage of requests that were rate limited."""
        if self.total_requests == 0:
            return 0.0
        return (self.rate_limited_requests / self.total_requests) * 100


class MetricsCollector:
    """
    Centralized metrics collection and aggregation.
    Thread-safe implementation with configurable retention.
    """
    
    def __init__(self, retention_hours: int = 24, max_request_history: int = 10000):
        """
        Initialize metrics collector.
        
        Args:
            retention_hours: How long to keep detailed metrics
            max_request_history: Maximum number of request records to keep
        """
        self.retention_hours = retention_hours
        self.max_request_history = max_request_history
        
        # Thread safety
        self._lock = Lock()
        
        # Request tracking
        self.request_history: deque = deque(maxlen=max_request_history)
        self.endpoint_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'count': 0,
            'total_response_time': 0.0,
            'min_response_time': float('inf'),
            'max_response_time': 0.0,
            'error_count': 0,
            'cache_hits': 0,
            'rate_limited': 0
        })
        
        # Cache metrics
        self.cache_metrics = CacheMetrics()
        self.cache_stats_by_prefix: Dict[str, CacheMetrics] = defaultdict(CacheMetrics)
        
        # Rate limiting metrics
        self.rate_limit_metrics = RateLimitMetrics()
        
        # System metrics
        self.start_time = datetime.now()
        self.last_cleanup = datetime.now()
    
    def record_request(self, metrics: RequestMetrics):
        """
        Record metrics for an API request.
        
        Args:
            metrics: RequestMetrics object with request details
        """
        with self._lock:
            # Add to request history
            self.request_history.append(metrics)
            
            # Update endpoint statistics
            endpoint_key = f"{metrics.method} {metrics.endpoint}"
            stats = self.endpoint_stats[endpoint_key]
            
            stats['count'] += 1
            stats['total_response_time'] += metrics.response_time_ms
            stats['min_response_time'] = min(stats['min_response_time'], metrics.response_time_ms)
            stats['max_response_time'] = max(stats['max_response_time'], metrics.response_time_ms)
            
            if metrics.status_code >= 400:
                stats['error_count'] += 1
            
            if metrics.cache_hit:
                stats['cache_hits'] += 1
            
            if metrics.rate_limited:
                stats['rate_limited'] += 1
    
    def record_cache_hit(self, cache_key_prefix: str = ""):
        """Record a cache hit."""
        with self._lock:
            self.cache_metrics.hits += 1
            self.cache_metrics.total_requests += 1
            
            if cache_key_prefix:
                self.cache_stats_by_prefix[cache_key_prefix].hits += 1
                self.cache_stats_by_prefix[cache_key_prefix].total_requests += 1
    
    def record_cache_miss(self, cache_key_prefix: str = ""):
        """Record a cache miss."""
        with self._lock:
            self.cache_metrics.misses += 1
            self.cache_metrics.total_requests += 1
            
            if cache_key_prefix:
                self.cache_stats_by_prefix[cache_key_prefix].misses += 1
                self.cache_stats_by_prefix[cache_key_prefix].total_requests += 1
    
    def record_cache_set(self, cache_key_prefix: str = ""):
        """Record a cache set operation."""
        with self._lock:
            self.cache_metrics.sets += 1
            
            if cache_key_prefix:
                self.cache_stats_by_prefix[cache_key_prefix].sets += 1
    
    def record_cache_delete(self, cache_key_prefix: str = ""):
        """Record a cache delete operation."""
        with self._lock:
            self.cache_metrics.deletes += 1
            
            if cache_key_prefix:
                self.cache_stats_by_prefix[cache_key_prefix].deletes += 1
    
    def record_cache_error(self, cache_key_prefix: str = ""):
        """Record a cache error."""
        with self._lock:
            self.cache_metrics.errors += 1
            
            if cache_key_prefix:
                self.cache_stats_by_prefix[cache_key_prefix].errors += 1
    
    def record_rate_limit_hit(self, endpoint: str):
        """Record a rate limit hit."""
        with self._lock:
            self.rate_limit_metrics.total_requests += 1
            self.rate_limit_metrics.rate_limited_requests += 1
            self.rate_limit_metrics.endpoint_hits[endpoint] = (
                self.rate_limit_metrics.endpoint_hits.get(endpoint, 0) + 1
            )
    
    def record_rate_limit_bypass(self, endpoint: str):
        """Record a rate limit bypass."""
        with self._lock:
            self.rate_limit_metrics.total_requests += 1
            self.rate_limit_metrics.bypassed_requests += 1
    
    def record_normal_request(self, endpoint: str):
        """Record a normal request (not rate limited)."""
        with self._lock:
            self.rate_limit_metrics.total_requests += 1
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics for all collected metrics.
        
        Returns:
            Dictionary with comprehensive metrics summary
        """
        with self._lock:
            # Clean up old data
            self._cleanup_old_data()
            
            # Calculate time-based stats
            now = datetime.now()
            uptime_seconds = (now - self.start_time).total_seconds()
            
            # Request stats
            total_requests = len(self.request_history)
            requests_per_minute = 0.0
            if uptime_seconds > 0:
                requests_per_minute = (total_requests / uptime_seconds) * 60
            
            # Response time stats
            response_times = [r.response_time_ms for r in self.request_history]
            avg_response_time = sum(response_times) / len(response_times) if response_times else 0
            
            # Status code distribution
            status_codes = defaultdict(int)
            for request in self.request_history:
                status_codes[str(request.status_code)] += 1
            
            # Top endpoints
            top_endpoints = sorted(
                self.endpoint_stats.items(),
                key=lambda x: x[1]['count'],
                reverse=True
            )[:10]
            
            return {
                "system": {
                    "uptime_seconds": uptime_seconds,
                    "start_time": self.start_time.isoformat(),
                    "last_cleanup": self.last_cleanup.isoformat()
                },
                "requests": {
                    "total": total_requests,
                    "per_minute": round(requests_per_minute, 2),
                    "avg_response_time_ms": round(avg_response_time, 2),
                    "status_codes": dict(status_codes)
                },
                "cache": {
                    "hit_rate": round(self.cache_metrics.hit_rate, 2),
                    "miss_rate": round(self.cache_metrics.miss_rate, 2),
                    "total_operations": {
                        "hits": self.cache_metrics.hits,
                        "misses": self.cache_metrics.misses,
                        "sets": self.cache_metrics.sets,
                        "deletes": self.cache_metrics.deletes,
                        "errors": self.cache_metrics.errors
                    },
                    "by_prefix": {
                        prefix: {
                            "hit_rate": round(metrics.hit_rate, 2),
                            "operations": {
                                "hits": metrics.hits,
                                "misses": metrics.misses,
                                "sets": metrics.sets,
                                "deletes": metrics.deletes,
                                "errors": metrics.errors
                            }
                        }
                        for prefix, metrics in self.cache_stats_by_prefix.items()
                    }
                },
                "rate_limiting": {
                    "total_requests": self.rate_limit_metrics.total_requests,
                    "rate_limited": self.rate_limit_metrics.rate_limited_requests,
                    "bypassed": self.rate_limit_metrics.bypassed_requests,
                    "rate_limit_percentage": round(self.rate_limit_metrics.rate_limit_percentage, 2),
                    "endpoint_hits": dict(self.rate_limit_metrics.endpoint_hits)
                },
                "endpoints": {
                    endpoint: {
                        "count": stats['count'],
                        "avg_response_time_ms": round(
                            stats['total_response_time'] / max(stats['count'], 1), 2
                        ),
                        "min_response_time_ms": stats['min_response_time'] if stats['min_response_time'] != float('inf') else 0,
                        "max_response_time_ms": stats['max_response_time'],
                        "error_rate": round(
                            (stats['error_count'] / max(stats['count'], 1)) * 100, 2
                        ),
                        "cache_hit_rate": round(
                            (stats['cache_hits'] / max(stats['count'], 1)) * 100, 2
                        )
                    }
                    for endpoint, stats in dict(top_endpoints)
                }
            }
    
    def get_recent_requests(self, minutes: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent requests within the specified time window.
        
        Args:
            minutes: Number of minutes to look back
            
        Returns:
            List of recent request data
        """
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self._lock:
            recent_requests = [
                {
                    "endpoint": req.endpoint,
                    "method": req.method,
                    "status_code": req.status_code,
                    "response_time_ms": req.response_time_ms,
                    "timestamp": req.timestamp.isoformat(),
                    "client_ip": req.client_ip,
                    "cache_hit": req.cache_hit,
                    "rate_limited": req.rate_limited
                }
                for req in self.request_history
                if req.timestamp >= cutoff_time
            ]
        
        return recent_requests
    
    def reset_metrics(self):
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self.request_history.clear()
            self.endpoint_stats.clear()
            self.cache_metrics = CacheMetrics()
            self.cache_stats_by_prefix.clear()
            self.rate_limit_metrics = RateLimitMetrics()
            self.start_time = datetime.now()
            self.last_cleanup = datetime.now()
    
    def _cleanup_old_data(self):
        """Remove data older than the retention period."""
        now = datetime.now()
        cutoff_time = now - timedelta(hours=self.retention_hours)
        
        # Clean up request history
        while self.request_history and self.request_history[0].timestamp < cutoff_time:
            self.request_history.popleft()
        
        self.last_cleanup = now


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """
    Get the global metrics collector instance.
    
    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def setup_monitoring():
    """Initialize monitoring system."""
    collector = get_metrics_collector()
    logger.info("Monitoring system initialized successfully")
    return collector


# Convenience functions for recording metrics
def record_request_metrics(endpoint: str, method: str, status_code: int, 
                         response_time_ms: float, client_ip: str,
                         user_agent: Optional[str] = None, cache_hit: bool = False,
                         rate_limited: bool = False):
    """Convenience function to record request metrics."""
    metrics = RequestMetrics(
        endpoint=endpoint,
        method=method,
        status_code=status_code,
        response_time_ms=response_time_ms,
        timestamp=datetime.now(),
        client_ip=client_ip,
        user_agent=user_agent,
        cache_hit=cache_hit,
        rate_limited=rate_limited
    )
    get_metrics_collector().record_request(metrics)


def record_cache_operation(operation: str, cache_key_prefix: str = ""):
    """Convenience function to record cache operations."""
    collector = get_metrics_collector()
    
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


def get_monitoring_data() -> Dict[str, Any]:
    """Get comprehensive monitoring data."""
    return get_metrics_collector().get_summary_stats()