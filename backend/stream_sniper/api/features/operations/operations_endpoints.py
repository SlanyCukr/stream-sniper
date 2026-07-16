"""Operational health, metrics, cache, and API information endpoints."""

import time
from datetime import datetime

from fastapi import APIRouter, Depends, Request, Response

from ....logging_config import get_logger
from ...caching.cache import InProcessCache
from ...config import APIConfig
from ...dependencies import get_cache, get_config, get_health_checker, get_metrics_collector
from ...observability.health import HealthChecker
from ...observability.health import HealthStatus as HealthStatusEnum
from ...observability.monitoring import MetricsCollector, collect_monitoring_snapshot
from ...security.auth import get_current_admin_user
from ...security.auth_models import UserInDB
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import RateLimitErrorResponse
from .operations_models import (
    ApiEndpointLinks,
    ApiFeatureFlags,
    ApiInfoResponse,
    CacheBackendStatsResponse,
    CacheFlushResponse,
    CacheMetricsResponse,
    CacheStatsResponse,
    DetailedHealthStatusResponse,
    DetailedSystemResponse,
    DiskResourceResponse,
    HealthStatusResponse,
    MemoryResourceResponse,
    MetricsResponse,
    SystemResourcesResponse,
)

logger = get_logger(__name__)
MILLISECONDS_PER_SECOND = 1_000

router = APIRouter()
admin_router = APIRouter(dependencies=[Depends(get_current_admin_user)])


@router.get(
    "/health",
    response_model=HealthStatusResponse,
    tags=["Health"],
    summary="Basic Health Check",
    description="Check critical API dependencies for load balancers and probes.",
)
@limiter.limit(rate_limits.HEALTH)
def health_check(
    request: Request,
    response: Response,
    health: HealthChecker = Depends(get_health_checker),
    config: APIConfig = Depends(get_config),
) -> HealthStatusResponse:
    """Return basic health, with 503 for unhealthy critical components."""
    try:
        overall_status, health_data = health.get_basic_health()
        response.status_code = 503 if overall_status in [HealthStatusEnum.UNHEALTHY, HealthStatusEnum.CRITICAL] else 200
        return HealthStatusResponse.model_validate(health_data)
    except Exception:
        logger.exception("Health check failed")
        response.status_code = 503
        return HealthStatusResponse(
            status="critical",
            database=None,
            timestamp=datetime.now().isoformat() + "Z",
            version=config.version,
            uptime_seconds=None,
            error="Health check unavailable",
        )


@admin_router.get(
    "/health/detailed",
    response_model=DetailedHealthStatusResponse,
    tags=["Health"],
    summary="Detailed Health Check",
    description="Check component health, system resources, and external dependencies.",
)
@limiter.limit(rate_limits.HEALTH)
def detailed_health_check(
    request: Request,
    response: Response,
    health: HealthChecker = Depends(get_health_checker),
    config: APIConfig = Depends(get_config),
) -> DetailedHealthStatusResponse:
    """Return detailed health, with 503 only for unhealthy critical components."""
    try:
        overall_status, health_data = health.get_detailed_health()
        response.status_code = 503 if overall_status in [HealthStatusEnum.UNHEALTHY, HealthStatusEnum.CRITICAL] else 200
        return DetailedHealthStatusResponse.model_validate(health_data)
    except Exception:
        logger.exception("Detailed health check failed")
        response.status_code = 503
        return DetailedHealthStatusResponse(
            status="critical",
            timestamp=datetime.now().isoformat() + "Z",
            version=config.version,
            uptime_seconds=0.0,
            components={},
            system=DetailedSystemResponse(
                platform="unavailable",
                python_version="unavailable",
                cpu_count=None,
                resources=SystemResourcesResponse(
                    cpu_percent=0,
                    memory=MemoryResourceResponse(percent=0, available_mb=0, used_mb=0, total_mb=0),
                    disk=DiskResourceResponse(percent=0, free_gb=0, total_gb=0),
                    load_average=None,
                    uptime_seconds=0,
                ),
            ),
            error="Detailed health check unavailable",
        )


@admin_router.get(
    "/metrics/prometheus",
    tags=["Monitoring"],
    summary="Prometheus Metrics",
    description="Return component and system metrics in Prometheus exposition format.",
)
@limiter.limit(rate_limits.GENERAL)
def prometheus_metrics(
    request: Request,
    response: Response,
    health: HealthChecker = Depends(get_health_checker),
) -> Response:
    """Get Prometheus-compatible metrics."""
    try:
        metrics_text = health.generate_prometheus_metrics()
        return Response(content=metrics_text, media_type="text/plain; version=0.0.4")
    except Exception as exc:
        logger.exception(f"Failed to generate Prometheus metrics: {exc}")
        error_time = int(time.time() * MILLISECONDS_PER_SECOND)
        return Response(
            content=(
                "# HELP stream_sniper_metrics_error Error generating metrics\n"
                "# TYPE stream_sniper_metrics_error gauge\n"
                f"stream_sniper_metrics_error 1 {error_time}\n"
            ),
            media_type="text/plain; version=0.0.4",
        )


@admin_router.get(
    "/metrics",
    response_model=MetricsResponse,
    tags=["Monitoring"],
    summary="API Performance Metrics",
    description="Return request, cache, rate-limit, endpoint, and system metrics.",
    responses={429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.GENERAL)
def get_metrics(
    request: Request,
    response: Response,
    metrics: MetricsCollector = Depends(get_metrics_collector),
) -> MetricsResponse:
    return MetricsResponse.model_validate(collect_monitoring_snapshot(metrics))


@admin_router.get(
    "/cache/stats",
    response_model=CacheStatsResponse,
    tags=["Monitoring"],
    summary="Cache Statistics",
    description="Return cache health and cache-performance metrics.",
    responses={429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.GENERAL)
def get_cache_stats(
    request: Request,
    response: Response,
    cache: InProcessCache = Depends(get_cache),
    metrics: MetricsCollector = Depends(get_metrics_collector),
) -> CacheStatsResponse:
    cache_stats = cache.get_stats()
    summary = metrics.prune_and_summarize_metrics()
    return CacheStatsResponse(
        cache_stats=CacheBackendStatsResponse.model_validate(cache_stats),
        performance_metrics=CacheMetricsResponse.model_validate(summary["cache"]),
        timestamp=datetime.now().isoformat() + "Z",
    )


@admin_router.post(
    "/cache/flush",
    response_model=CacheFlushResponse,
    tags=["Monitoring"],
    summary="Flush Cache",
    description="Flush all cached data so subsequent requests repopulate the cache.",
    responses={429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.HEAVY)
def flush_cache(
    request: Request,
    response: Response,
    cache: InProcessCache = Depends(get_cache),
    current_user: UserInDB = Depends(get_current_admin_user),
) -> CacheFlushResponse:
    cache.flush_all()
    logger.info("Cache flushed by admin user id %s", current_user.id)
    return CacheFlushResponse(message="Cache flushed successfully", timestamp=datetime.now().isoformat() + "Z")


@router.get(
    "/",
    response_model=ApiInfoResponse,
    tags=["API Info"],
    summary="API Information",
    description="Get basic Stream Sniper API information.",
)
def root(request: Request, config: APIConfig = Depends(get_config)) -> ApiInfoResponse:
    """Welcome endpoint with API information."""
    return ApiInfoResponse(
        name=config.title,
        version=config.version,
        description=config.description,
        docs="/docs",
        redoc="/redoc",
        features=ApiFeatureFlags(
            caching=config.cache.enabled,
            rate_limiting=config.rate_limit.enabled,
            compression=config.compression.enabled,
            monitoring=config.monitoring.enabled,
        ),
        endpoints=ApiEndpointLinks(
            health="/health",
            health_detailed="/health/detailed",
            metrics="/metrics",
            prometheus_metrics="/metrics/prometheus",
            cache_stats="/cache/stats",
        ),
    )


router.include_router(admin_router)
