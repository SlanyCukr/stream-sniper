import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import uvicorn as uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Path, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from pydantic import BaseModel, Field
from slowapi.util import get_remote_address

from ..database.connection_pool import close_pool
from ..database.creator_table_gateway import select_creator_top_chatters_db, select_creators_db
from ..logging_config import get_logger, setup_logging
from .auth_endpoints import router as auth_router
from .cache import CacheTTL, get_cache, warm_cache
from .chatter_endpoints import router as chatter_router

# Import our new modules
from .config import get_config
from .health import HealthStatus as HealthStatusEnum
from .health import get_health_checker
from .middleware import setup_middleware
from .models import ErrorResponse
from .monitoring import (
    get_metrics_collector,
    get_monitoring_data,
    record_cache_operation,
    record_request_metrics,
    setup_monitoring,
)
from .rate_limiter import limiter, rate_limits, setup_rate_limiting
from .stream_endpoints import router as stream_router
from .tracking_endpoints import router as tracking_router

load_dotenv()

# Setup structured logging
setup_logging(environment="production")
logger = get_logger(__name__)

# Get configuration
config = get_config()
if not config.validate():
    raise RuntimeError("Invalid configuration. Please check your environment variables.")


# Pydantic Models for API Documentation


class HealthStatus(BaseModel):
    """Basic health status (database is the only critical component checked)"""

    status: str = Field(..., description="Overall health status", json_schema_extra={"example": "healthy"})
    database: Optional[Dict[str, Any]] = Field(None, description="Database connection pool status")
    timestamp: str = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version", json_schema_extra={"example": "1.0.0"})
    uptime_seconds: Optional[float] = Field(None, description="Application uptime in seconds")
    error: Optional[str] = Field(None, description="Error detail when the health check itself fails")


class DetailedHealthStatus(BaseModel):
    """Comprehensive health status with system metrics"""

    status: str = Field(..., description="Overall health status", json_schema_extra={"example": "healthy"})
    timestamp: str = Field(..., description="Health check timestamp")
    version: str = Field(..., description="API version", json_schema_extra={"example": "1.0.0"})
    uptime_seconds: float = Field(..., description="Application uptime in seconds")
    components: Dict[str, Any] = Field(..., description="Component health status")
    system: Dict[str, Any] = Field(..., description="System metrics and information")


class MetricsResponse(BaseModel):
    """API metrics and monitoring data"""

    system: Dict[str, Any] = Field(..., description="System metrics")
    requests: Dict[str, Any] = Field(..., description="Request statistics")
    cache: Dict[str, Any] = Field(..., description="Cache performance metrics")
    rate_limiting: Dict[str, Any] = Field(..., description="Rate limiting metrics")
    endpoints: Dict[str, Any] = Field(..., description="Per-endpoint statistics")


# Tags for endpoint organization
tags_metadata = [
    {"name": "Authentication", "description": "User authentication, registration, and account management"},
    {"name": "Tracking", "description": "Automated streamer tracking and processing management"},
    {"name": "Chatters", "description": "Operations related to chat participants and their messages"},
    {"name": "Streams", "description": "Stream information, analytics, and chat data"},
    {"name": "Creators", "description": "Twitch creator/streamer information"},
    {"name": "Health", "description": "API health monitoring and connection pool status"},
    {"name": "Monitoring", "description": "Performance metrics and monitoring endpoints"},
    {"name": "API Info", "description": "General API information and documentation"},
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: warm caches on startup, close resources on shutdown."""
    logger.info("Starting Stream Sniper API...")

    if config.cache.enabled and config.cache.warm_on_startup:
        try:
            warm_cache()
            logger.info("Cache warming completed")
        except Exception as e:
            logger.warning(f"Cache warming failed: {e}")

    logger.info(f"API started successfully on {config.host}:{config.port}")

    yield

    logger.info("Shutting down Stream Sniper API...")
    try:
        close_pool()
        logger.info("Database connection pool closed")
    except Exception as e:
        logger.warning(f"Error closing connection pool: {e}")


# FastAPI App Configuration
app = FastAPI(
    lifespan=lifespan,
    title=config.title,
    description="""
    A comprehensive Twitch stream analytics API that provides access to chat data, 
    stream statistics, and user interaction analytics from Twitch VODs.
    
    ## Features
    
    * **Authentication**: Secure user registration, login, and JWT-based authentication
    * **Stream Analytics**: Get detailed information about Twitch streams including message counts, duration, and metadata
    * **Chat Analysis**: Access chat messages, most active chatters, and interaction patterns
    * **Creator Insights**: Track creator participation across different streams
    * **User Analytics**: Analyze individual chatter behavior and message history
    * **Tagging Analytics**: Discover most mentioned/tagged users in chat
    * **Performance**: Built-in caching and rate limiting for optimal performance
    * **Monitoring**: Comprehensive metrics and health monitoring
    
    ## Authentication
    
    * **JWT Tokens**: Secure authentication using JSON Web Tokens
    * **Role-based Access**: Support for user and admin roles
    * **Password Security**: Bcrypt password hashing
    * **User Management**: Registration, login, profile updates, and admin controls
    
    ## Performance Features
    
    * **Caching**: Intelligent in-process caching of expensive database queries
    * **Rate Limiting**: Configurable rate limits to prevent abuse
    * **Response Compression**: Automatic compression for large responses
    * **Health Monitoring**: Real-time health checks and performance metrics
    
    ## Data Source
    
    All data is collected from publicly available Twitch VOD chat logs and processed 
    to provide meaningful analytics and insights.
    """,
    version=config.version,
    contact={
        "name": "Stream Sniper",
        "url": "https://github.com/your-repo/stream-sniper",
    },
    license_info={
        "name": "MIT",
    },
    servers=[{"url": f"http://localhost:{config.port}", "description": "Development server"}],
    openapi_tags=tags_metadata,
)

# Setup structured logging middleware
setup_middleware(app, config)

# Setup middleware
if config.cors_enabled:
    origins = config.cors_origins.split(",") if config.cors_origins != "*" else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=config.cors_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add compression middleware
if config.compression.enabled:
    app.add_middleware(
        GZipMiddleware, minimum_size=config.compression.min_size, compresslevel=config.compression.compression_level
    )

# Setup rate limiting
if config.rate_limit.enabled:
    setup_rate_limiting(app)

# Setup monitoring
if config.monitoring.enabled:
    setup_monitoring()

# Include authentication router
app.include_router(auth_router)

# Include chatter router
app.include_router(chatter_router)

# Include stream router
app.include_router(stream_router)

# Include tracking router
app.include_router(tracking_router)


# Middleware for request metrics
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware to collect request metrics."""
    start_time = time.time()

    # Process request
    response = await call_next(request)

    # Calculate metrics
    response_time_ms = (time.time() - start_time) * 1000
    client_ip = get_remote_address(request)
    user_agent = request.headers.get("user-agent")

    # Check if response came from cache
    cache_hit = response.headers.get("X-Cache") == "HIT"

    # Check if request was rate limited
    rate_limited = response.status_code == 429

    # Record metrics
    if config.monitoring.collect_request_metrics:
        record_request_metrics(
            endpoint=str(request.url.path),
            method=request.method,
            status_code=response.status_code,
            response_time_ms=response_time_ms,
            client_ip=client_ip,
            user_agent=user_agent,
            cache_hit=cache_hit,
            rate_limited=rate_limited,
        )

    # Add health check specific headers
    if request.url.path.startswith("/health"):
        response.headers["X-Health-Check"] = "true"
        response.headers["X-Health-Response-Time"] = str(round(response_time_ms, 2))

    return response




@app.get(
    "/creators",
    response_model=List[List[Any]],
    tags=["Creators"],
    summary="Get all creators",
    description=f"""
    Retrieve a list of all Twitch creators/streamers in the database.
    Each creator entry contains their ID and display name.
    
    **Rate Limit**: {rate_limits.GENERAL}
    """,
    responses={
        200: {
            "description": "List of all creators",
            "content": {
                "application/json": {
                    "example": [[1, "Amazing Streamer"], [2, "Pro Gamer"], [3, "Chat Master"], [4, "Stream Legend"]]
                }
            },
        },
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def get_creators(request: Request, response: Response):
    """Get all creators in the database"""
    try:
        # Try cache first
        cache = get_cache()
        cache_key = cache._generate_key("creators")
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "creators")
            return cached_result

        # Cache miss - fetch from database
        record_cache_operation("miss", "creators")
        result = select_creators_db()

        # Cache the result
        cache.set(cache_key, result, CacheTTL.CREATORS)
        record_cache_operation("set", "creators")
        response.headers["X-Cache"] = "MISS"

        return result
    except Exception as e:
        logger.error(f"Error fetching creators: {e}")
        record_cache_operation("error", "creators")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/creator/{creator_id}/top-chatters",
    response_model=List[List[Any]],
    tags=["Creators"],
    summary="Get a creator's most active chatters",
    description=f"""
    Retrieve the most active chatters across ALL of a creator's streams.
    Returns a list of [chatter_id, nick, message_count] tuples ordered by
    message count descending.

    An empty list is returned when the creator has no chat activity.

    **Rate Limit**: {rate_limits.GENERAL}
    """,
    responses={
        200: {
            "description": "List of the creator's most active chatters",
            "content": {
                "application/json": {
                    "example": [[42, "chatty_user", 1250], [15, "regular_viewer", 980], [7, "stream_fan", 640]]
                }
            },
        },
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def get_creator_top_chatters(
    request: Request,
    response: Response,
    creator_id: int = Path(..., description="Unique creator ID", json_schema_extra={"example": 5}),
    limit: int = Query(25, ge=1, le=200, description="Maximum number of chatters to return", json_schema_extra={"example": 25}),
):
    """Get the most active chatters across all of a creator's streams"""
    try:
        # Try cache first
        cache = get_cache()
        cache_key = cache._generate_key("creator_top_chatters", creator_id, limit)
        cached_result = cache.get(cache_key)

        if cached_result is not None:
            response.headers["X-Cache"] = "HIT"
            record_cache_operation("hit", "creator_top_chatters")
            return cached_result

        # Cache miss - fetch from database
        record_cache_operation("miss", "creator_top_chatters")
        result = select_creator_top_chatters_db(creator_id, limit)

        # Cache the result (an empty list is a valid, cacheable state)
        cache.set(cache_key, result, CacheTTL.STREAM_DETAILS)
        record_cache_operation("set", "creator_top_chatters")
        response.headers["X-Cache"] = "MISS"

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching creator top chatters: {e}")
        record_cache_operation("error", "creator_top_chatters")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get(
    "/health",
    response_model=HealthStatus,
    tags=["Health"],
    summary="Basic Health Check",
    description=f"""
    Basic health check endpoint for load balancer health checks.
    Only checks critical components (database connectivity).
    
    Returns 200 if system is operational, 503 if critical issues exist.
    
    **Rate Limit**: {rate_limits.HEALTH}
    """,
    responses={
        200: {
            "description": "System is healthy",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "timestamp": "2024-01-15T20:30:15Z",
                        "version": "1.0.0",
                        "uptime_seconds": 3600,
                        "database": {"status": "healthy", "healthy": True, "response_time_ms": 5.2},
                    }
                }
            },
        },
        503: {
            "description": "System is unhealthy - critical issues detected",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "timestamp": "2024-01-15T20:30:15Z",
                        "version": "1.0.0",
                        "uptime_seconds": 3600,
                        "database": {"status": "critical", "healthy": False, "response_time_ms": 5000},
                    }
                }
            },
        },
    },
)
@limiter.limit(rate_limits.HEALTH)
def health_check(request: Request, response: Response):
    """Basic health check endpoint for load balancers"""
    try:
        health_checker = get_health_checker()
        overall_status, health_data = health_checker.get_basic_health()

        # Set HTTP status code based on health
        if overall_status in [HealthStatusEnum.UNHEALTHY, HealthStatusEnum.CRITICAL]:
            response.status_code = 503
        else:
            response.status_code = 200

        return health_data

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        response.status_code = 503
        return {
            "status": "critical",
            "timestamp": datetime.now().isoformat() + "Z",
            "version": config.version,
            "error": str(e),
        }


@app.get(
    "/health/detailed",
    response_model=DetailedHealthStatus,
    tags=["Health"],
    summary="Detailed Health Check",
    description=f"""
    Comprehensive health check with detailed system monitoring.
    
    Includes:
    * All system components (database, cache, rate limiter, external APIs)
    * System resource utilization (CPU, memory, disk)
    * Component response times and detailed status
    * External dependency checks (Twitch API)
    
    **Rate Limit**: {rate_limits.HEALTH}
    """,
    responses={
        200: {
            "description": "Detailed system health information",
        },
        503: {
            "description": "System has critical issues",
        },
    },
)
@limiter.limit(rate_limits.HEALTH)
def detailed_health_check(request: Request, response: Response):
    """Comprehensive health check with system metrics"""
    try:
        health_checker = get_health_checker()
        overall_status, health_data = health_checker.get_detailed_health()

        # Set HTTP status code based on health
        if overall_status in [HealthStatusEnum.UNHEALTHY, HealthStatusEnum.CRITICAL]:
            response.status_code = 503
        elif overall_status == HealthStatusEnum.DEGRADED:
            response.status_code = 200  # Degraded is still operational
        else:
            response.status_code = 200

        return health_data

    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        response.status_code = 503
        return {
            "status": "critical",
            "timestamp": datetime.now().isoformat() + "Z",
            "version": config.version,
            "error": str(e),
        }


@app.get(
    "/metrics/prometheus",
    tags=["Monitoring"],
    summary="Prometheus Metrics",
    description=f"""
    Prometheus-compatible metrics endpoint for monitoring systems.
    
    Returns metrics in Prometheus exposition format including:
    * Component health status (as numeric values)
    * Component response times
    * System resource utilization
    * Application uptime
    
    **Rate Limit**: {rate_limits.GENERAL}
    """,
    responses={
        200: {
            "description": "Prometheus metrics in text format",
            "content": {
                "text/plain": {
                    "example": """# HELP stream_sniper_component_health Health status of system components
# TYPE stream_sniper_component_health gauge
stream_sniper_component_health{component="database"} 1.0
stream_sniper_component_health{component="cache"} 1.0
"""
                }
            },
        }
    },
)
@limiter.limit(rate_limits.GENERAL)
def prometheus_metrics(request: Request, response: Response):
    """Get Prometheus-compatible metrics"""
    try:
        health_checker = get_health_checker()
        metrics_text = health_checker.generate_prometheus_metrics()

        return Response(content=metrics_text, media_type="text/plain; version=0.0.4")

    except Exception as e:
        logger.error(f"Failed to generate Prometheus metrics: {e}")
        error_time = int(time.time() * 1000)
        error_metrics = f"""# HELP stream_sniper_metrics_error Error generating metrics
# TYPE stream_sniper_metrics_error gauge
stream_sniper_metrics_error 1 {error_time}
"""
        return Response(content=error_metrics, media_type="text/plain; version=0.0.4")


# Monitoring endpoints
@app.get(
    "/metrics",
    response_model=MetricsResponse,
    tags=["Monitoring"],
    summary="API Performance Metrics",
    description=f"""
    Get comprehensive performance metrics and monitoring data.
    
    Includes:
    * Request statistics and response times
    * Cache hit/miss rates and performance
    * Rate limiting statistics
    * Per-endpoint performance metrics
    * System uptime and health
    
    **Rate Limit**: {rate_limits.GENERAL}
    """,
    responses={
        200: {
            "description": "Performance metrics data",
        },
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def get_metrics(request: Request, response: Response):
    """Get comprehensive API performance metrics"""
    try:
        metrics_data = get_monitoring_data()
        return metrics_data
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch metrics")


@app.get(
    "/cache/stats",
    tags=["Monitoring"],
    summary="Cache Statistics",
    description=f"""
    Get detailed cache performance statistics.
    
    **Rate Limit**: {rate_limits.GENERAL}
    """,
    responses={
        200: {
            "description": "Cache statistics",
        },
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.GENERAL)
def get_cache_stats(request: Request, response: Response):
    """Get detailed cache performance statistics"""
    try:
        cache = get_cache()
        cache_stats = cache.get_stats()

        # Add metrics from monitoring
        collector = get_metrics_collector()
        summary = collector.get_summary_stats()

        return {
            "cache_stats": cache_stats,
            "performance_metrics": summary.get("cache", {}),
            "timestamp": datetime.now().isoformat() + "Z",
        }
    except Exception as e:
        logger.error(f"Error fetching cache stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch cache statistics")


@app.post(
    "/cache/flush",
    tags=["Monitoring"],
    summary="Flush Cache",
    description=f"""
    Flush all cached data. Use with caution as this will impact performance
    until cache is rebuilt.
    
    **Rate Limit**: {rate_limits.HEAVY}
    """,
    responses={
        200: {
            "description": "Cache flushed successfully",
        },
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
    },
)
@limiter.limit(rate_limits.HEAVY)
def flush_cache(request: Request, response: Response):
    """Flush all cached data"""
    try:
        cache = get_cache()
        success = cache.flush_all()

        if success:
            return {"message": "Cache flushed successfully", "timestamp": datetime.now().isoformat() + "Z"}
        else:
            raise HTTPException(status_code=500, detail="Failed to flush cache")
    except Exception as e:
        logger.error(f"Error flushing cache: {e}")
        raise HTTPException(status_code=500, detail="Failed to flush cache")


# Root endpoint for API information
@app.get(
    "/", tags=["API Info"], summary="API Information", description="Get basic information about the Stream Sniper API"
)
def root():
    """Welcome endpoint with API information"""
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


if __name__ == "__main__":
    uvicorn.run(app, host=config.host, port=config.port, log_level="info" if not config.debug else "debug")
