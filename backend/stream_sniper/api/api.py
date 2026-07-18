"""FastAPI application factory and production ASGI boundary."""

import time
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import RequestResponseEndpoint
from starlette.responses import Response

from ..database.core.connection_pool import enter_pool_scope, exit_pool_scope
from ..logging_config import get_logger
from .config import APIConfig, load_config
from .error_boundary import UnexpectedExceptionMiddleware
from .features.auth.auth_router import router as auth_router
from .features.chatters.chatter_endpoints import router as chatter_router
from .features.community.audience_endpoints import router as audience_router
from .features.community.community_endpoints import router as community_router
from .features.content.moment_endpoints import router as moment_router
from .features.content.scene_chatter_endpoints import router as scene_chatter_router
from .features.content.scene_endpoints import router as scene_router
from .features.content.scene_event_endpoints import router as scene_event_router
from .features.content.scene_highlights_endpoints import router as scene_highlights_router
from .features.content.scene_radar_endpoints import router as scene_radar_router
from .features.content.scene_trending_endpoints import router as scene_trending_router
from .features.content.scene_wrapped_endpoints import router as scene_wrapped_router
from .features.creators.analytics_endpoints import router as analytics_router
from .features.creators.creator_endpoints import router as creator_router
from .features.operations.operations_endpoints import router as operations_router
from .features.search.search_endpoints import router as search_router
from .features.streams.compare_endpoints import router as compare_router
from .features.streams.message_endpoints import router as message_router
from .features.streams.stream_endpoints import router as stream_router
from .features.streams.stream_insight_endpoints import router as stream_insight_router
from .features.streams.stream_report_endpoints import router as stream_report_router
from .features.streams.timeline_endpoints import router as timeline_router
from .features.tracking.tracking_router import router as tracking_router
from .middleware import setup_middleware
from .observability.monitoring import (
    RequestMetrics,
    enter_metrics_scope,
    exit_metrics_scope,
    record_request_metrics,
)
from .runtime import Runtime
from .security.auth import validate_auth_config
from .security.rate_limiter import setup_rate_limiting

logger = get_logger(__name__)
MILLISECONDS_PER_SECOND = 1_000
PROJECT_REPOSITORY_URL = "https://github.com/SlanyCukr/stream-sniper"

tags_metadata = [
    {"name": "Authentication", "description": "User authentication, registration, and account management"},
    {"name": "Tracking", "description": "Automated streamer tracking and processing management"},
    {"name": "Chatters", "description": "Operations related to chat participants and their messages"},
    {"name": "Streams", "description": "Stream information, analytics, and chat data"},
    {"name": "Creators", "description": "Twitch creator/streamer information"},
    {"name": "Search", "description": "Scene-wide chat message search and phrase origins"},
    {"name": "Health", "description": "API health monitoring and connection pool status"},
    {"name": "Monitoring", "description": "Performance metrics and monitoring endpoints"},
    {"name": "API Info", "description": "General API information and documentation"},
]

API_DESCRIPTION = """
A comprehensive Twitch stream analytics API that provides access to chat data,
stream statistics, and user interaction analytics from Twitch VODs.

## Features

* **Authentication**: Secure user registration, login, and JWT-based authentication
* **Stream Analytics**: Detailed stream information, message counts, and metadata
* **Chat Analysis**: Chat messages, active chatters, and interaction patterns
* **Performance**: In-process caching, rate limiting, and response compression
* **Monitoring**: Health checks and request metrics
"""


def _include_routers(app: FastAPI) -> None:
    """Mount the statically imported feature routers."""
    for router in (
        auth_router,
        chatter_router,
        # compare_router must precede stream_router: /streams/compare is a static
        # path that /streams/{stream_id} would otherwise capture (422 int_parsing).
        compare_router,
        stream_router,
        creator_router,
        tracking_router,
        operations_router,
        message_router,
        timeline_router,
        analytics_router,
        audience_router,
        stream_insight_router,
        stream_report_router,
        community_router,
        scene_router,
        scene_event_router,
        scene_chatter_router,
        scene_highlights_router,
        scene_trending_router,
        scene_wrapped_router,
        scene_radar_router,
        moment_router,
        search_router,
    ):
        app.include_router(router)


def create_app(
    config: APIConfig | None = None,
    runtime_factory: Callable[[APIConfig], Runtime] = Runtime,
) -> FastAPI:
    """Construct an application from an explicit configuration snapshot."""
    resolved = config or load_config()
    if not resolved.validate():
        raise RuntimeError("Invalid configuration. Please check your environment variables.")

    validate_auth_config(resolved.auth)

    runtime = runtime_factory(resolved)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        logger.info("Starting Stream Sniper API...")
        await runtime.startup()
        logger.info(f"API started successfully on {resolved.host}:{resolved.port}")
        yield
        logger.info("Shutting down Stream Sniper API...")
        await runtime.close()

    app = FastAPI(
        lifespan=lifespan,
        title=resolved.title,
        description=API_DESCRIPTION,
        version=resolved.version,
        contact={"name": "Stream Sniper", "url": PROJECT_REPOSITORY_URL},
        license_info={"name": "MIT"},
        openapi_tags=tags_metadata,
    )
    app.state.config = resolved
    app.state.runtime = runtime
    app.state.database_pool = runtime.database
    app.state.rate_limit_config = resolved.rate_limit

    setup_middleware(app, resolved)

    if resolved.cors_enabled:
        origins = resolved.cors_origins.split(",") if resolved.cors_origins != "*" else ["*"]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=resolved.cors_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    if resolved.compression.enabled:
        app.add_middleware(
            GZipMiddleware,
            minimum_size=resolved.compression.min_size,
            compresslevel=resolved.compression.compression_level,
        )

    setup_rate_limiting(app, resolved.rate_limit)

    _include_routers(app)

    @app.middleware("http")
    async def metrics_middleware(request: Request, call_next: RequestResponseEndpoint) -> Response:
        metrics_token = enter_metrics_scope(runtime.metrics)
        database_token = enter_pool_scope(runtime.database)
        start_time = time.time()
        try:
            response = await call_next(request)
            response_time_ms = (time.time() - start_time) * MILLISECONDS_PER_SECOND

            if resolved.monitoring.collect_request_metrics:
                record_request_metrics(
                    runtime.metrics,
                    RequestMetrics(
                        endpoint=str(request.url.path),
                        method=request.method,
                        status_code=response.status_code,
                        response_time_ms=response_time_ms,
                        timestamp=datetime.now(),
                        client_ip=get_remote_address(request),
                        user_agent=request.headers.get("user-agent"),
                        cache_hit=response.headers.get("X-Cache") == "HIT",
                        rate_limited=response.status_code == 429,
                    ),
                )

            if request.url.path.startswith("/health"):
                response.headers["X-Health-Check"] = "true"
                response.headers["X-Health-Response-Time"] = str(round(response_time_ms, 2))
            return response
        finally:
            exit_pool_scope(database_token)
            exit_metrics_scope(metrics_token)

    # Added last so it wraps request metrics and every route. TestClient sees the
    # same sanitized response as production instead of re-raising server errors.
    app.add_middleware(UnexpectedExceptionMiddleware)

    return app
