"""Operational health, metrics, cache, and API information endpoints."""

import time
from datetime import datetime
from typing import Any, cast

from fastapi import APIRouter, HTTPException, Request, Response

from ..logging_config import get_logger
from .cache import get_cache
from .config import get_config
from .health import HealthStatus as HealthStatusEnum
from .health import get_health_checker
from .models import DetailedHealthStatusResponse, ErrorResponse, HealthStatusResponse, MetricsResponse
from .monitoring import get_metrics_collector, get_monitoring_data
from .rate_limiter import limiter, rate_limits

logger = get_logger(__name__)
config = get_config()

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthStatusResponse,
    tags=["Health"],
    summary="Basic Health Check",
    description="Check critical API dependencies for load balancers and probes.",
)
@limiter.limit(rate_limits.HEALTH)
def health_check(request: Request, response: Response) -> dict[str, Any]:
    """Return basic health, with 503 for unhealthy critical components."""
    try:
        overall_status, health_data = get_health_checker().get_basic_health()
        response.status_code = 503 if overall_status in [HealthStatusEnum.UNHEALTHY, HealthStatusEnum.CRITICAL] else 200
        return cast(dict[str, Any], health_data)
    except Exception as exc:
        logger.error(f"Health check failed: {exc}")
        response.status_code = 503
        return {
            "status": "critical",
            "timestamp": datetime.now().isoformat() + "Z",
            "version": config.version,
            "error": str(exc),
        }


@router.get(
    "/health/detailed",
    response_model=DetailedHealthStatusResponse,
    tags=["Health"],
    summary="Detailed Health Check",
    description="Check component health, system resources, and external dependencies.",
)
@limiter.limit(rate_limits.HEALTH)
def detailed_health_check(request: Request, response: Response) -> dict[str, Any]:
    """Return detailed health, with 503 only for unhealthy critical components."""
    try:
        overall_status, health_data = get_health_checker().get_detailed_health()
        response.status_code = 503 if overall_status in [HealthStatusEnum.UNHEALTHY, HealthStatusEnum.CRITICAL] else 200
        return cast(dict[str, Any], health_data)
    except Exception as exc:
        logger.error(f"Detailed health check failed: {exc}")
        response.status_code = 503
        return {
            "status": "critical",
            "timestamp": datetime.now().isoformat() + "Z",
            "version": config.version,
            "error": str(exc),
        }


@router.get(
    "/metrics/prometheus",
    tags=["Monitoring"],
    summary="Prometheus Metrics",
    description="Return component and system metrics in Prometheus exposition format.",
)
@limiter.limit(rate_limits.GENERAL)
def prometheus_metrics(request: Request, response: Response) -> Response:
    """Get Prometheus-compatible metrics."""
    try:
        metrics_text = get_health_checker().generate_prometheus_metrics()
        return Response(content=metrics_text, media_type="text/plain; version=0.0.4")
    except Exception as exc:
        logger.error(f"Failed to generate Prometheus metrics: {exc}")
        error_time = int(time.time() * 1000)
        return Response(
            content=(
                "# HELP stream_sniper_metrics_error Error generating metrics\n"
                "# TYPE stream_sniper_metrics_error gauge\n"
                f"stream_sniper_metrics_error 1 {error_time}\n"
            ),
            media_type="text/plain; version=0.0.4",
        )


@router.get(
    "/metrics",
    response_model=MetricsResponse,
    tags=["Monitoring"],
    summary="API Performance Metrics",
    description="Return request, cache, rate-limit, endpoint, and system metrics.",
    responses={429: {"model": ErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.GENERAL)
def get_metrics(request: Request, response: Response) -> dict[str, Any]:
    """Get comprehensive API performance metrics."""
    try:
        return cast(dict[str, Any], get_monitoring_data())
    except Exception as exc:
        logger.error(f"Error fetching metrics: {exc}")
        raise HTTPException(status_code=500, detail="Failed to fetch metrics")


@router.get(
    "/cache/stats",
    tags=["Monitoring"],
    summary="Cache Statistics",
    description="Return cache health and cache-performance metrics.",
    responses={429: {"model": ErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.GENERAL)
def get_cache_stats(request: Request, response: Response) -> dict[str, Any]:
    """Get detailed cache performance statistics."""
    try:
        cache_stats = get_cache().get_stats()
        summary = get_metrics_collector().get_summary_stats()
        return {
            "cache_stats": cache_stats,
            "performance_metrics": summary.get("cache", {}),
            "timestamp": datetime.now().isoformat() + "Z",
        }
    except Exception as exc:
        logger.error(f"Error fetching cache stats: {exc}")
        raise HTTPException(status_code=500, detail="Failed to fetch cache statistics")


@router.post(
    "/cache/flush",
    tags=["Monitoring"],
    summary="Flush Cache",
    description="Flush all cached data so subsequent requests repopulate the cache.",
    responses={429: {"model": ErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.HEAVY)
def flush_cache(request: Request, response: Response) -> dict[str, str]:
    """Flush all cached data."""
    try:
        if get_cache().flush_all():
            return {"message": "Cache flushed successfully", "timestamp": datetime.now().isoformat() + "Z"}
        raise HTTPException(status_code=500, detail="Failed to flush cache")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Error flushing cache: {exc}")
        raise HTTPException(status_code=500, detail="Failed to flush cache")


@router.get("/", tags=["API Info"], summary="API Information", description="Get basic Stream Sniper API information.")
def root() -> dict[str, Any]:
    """Welcome endpoint with API information."""
    return {
        "name": config.title,
        "version": config.version,
        "description": config.description,
        "docs": "/docs",
        "redoc": "/redoc",
        "features": {
            "caching": config.cache.enabled,
            "rate_limiting": config.rate_limit.enabled,
            "compression": config.compression.enabled,
            "monitoring": config.monitoring.enabled,
        },
        "endpoints": {
            "health": "/health",
            "health_detailed": "/health/detailed",
            "metrics": "/metrics",
            "prometheus_metrics": "/metrics/prometheus",
            "cache_stats": "/cache/stats",
        },
    }
