"""
FastAPI middleware for Stream Sniper API.

This module provides middleware for correlation ID tracking, request/response logging,
and performance monitoring.
"""

import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from ..logging_config import correlation_context, get_logger

logger = get_logger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation IDs for request tracing."""

    def __init__(self, app, header_name: str = "X-Correlation-ID"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get correlation ID from header or generate new one
        correlation_id = request.headers.get(self.header_name) or str(uuid.uuid4())

        # Set correlation ID in context
        with correlation_context(correlation_id):
            # Add correlation ID to request state for access in endpoints
            request.state.correlation_id = correlation_id

            # Process request
            response = await call_next(request)

            # Add correlation ID to response headers
            response.headers[self.header_name] = correlation_id

            return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""

    def __init__(
        self,
        app,
        log_requests: bool = True,
        log_responses: bool = True,
        log_request_body: bool = False,
        log_response_body: bool = False,
        skip_paths: list = None,
    ):
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.skip_paths = skip_paths or ["/health", "/metrics", "/docs", "/openapi.json"]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        # Skip logging for certain paths
        if request.url.path in self.skip_paths:
            return await call_next(request)

        # Log request
        if self.log_requests:
            request_data = {
                "method": request.method,
                "url": str(request.url),
                "client_ip": self._get_client_ip(request),
                "user_agent": request.headers.get("user-agent", ""),
                "path": request.url.path,
                "query_params": dict(request.query_params),
            }

            if self.log_request_body and request.method in ["POST", "PUT", "PATCH"]:
                try:
                    # Note: This consumes the body, so we need to be careful
                    # In production, you might want to avoid logging large bodies
                    body = await request.body()
                    if len(body) < 1024:  # Only log small bodies
                        request_data["body_size"] = len(body)
                except Exception as e:
                    request_data["body_read_error"] = str(e)

            logger.info("HTTP request received", extra=request_data)

        # Process request
        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Log response
            if self.log_responses:
                response_data = {
                    "status_code": response.status_code,
                    "process_time_seconds": round(process_time, 3),
                    "method": request.method,
                    "path": request.url.path,
                }

                # Determine log level based on status code
                if response.status_code >= 500:
                    log_level = "error"
                elif response.status_code >= 400:
                    log_level = "warning"
                elif process_time > 5.0:  # Slow requests
                    log_level = "warning"
                    response_data["performance_warning"] = "slow_request"
                else:
                    log_level = "info"

                getattr(logger, log_level)("HTTP request completed", extra=response_data)

            return response

        except Exception as e:
            process_time = time.time() - start_time

            logger.error(
                "HTTP request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "process_time_seconds": round(process_time, 3),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        # Check for forwarded headers (when behind proxy)
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        # Fallback to direct client
        if hasattr(request.client, "host"):
            return request.client.host

        return "unknown"


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring API performance."""

    def __init__(self, app, slow_request_threshold: float = 2.0):
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            # Log performance metrics
            performance_data = {
                "endpoint": f"{request.method} {request.url.path}",
                "duration_seconds": round(process_time, 3),
                "status_code": response.status_code,
            }

            # Log slow requests as warnings
            if process_time > self.slow_request_threshold:
                performance_data["performance_issue"] = "slow_request"
                logger.warning("Slow API request detected", extra=performance_data)
            else:
                logger.debug("API request performance", extra=performance_data)

            # Add performance headers
            response.headers["X-Process-Time"] = str(round(process_time, 3))

            return response

        except Exception as e:
            process_time = time.time() - start_time

            logger.error(
                "API request failed",
                extra={
                    "endpoint": f"{request.method} {request.url.path}",
                    "duration_seconds": round(process_time, 3),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise


def setup_middleware(app, config=None):
    """Set up all middleware for the FastAPI application."""

    # Performance monitoring (first to track total time)
    app.add_middleware(
        PerformanceMonitoringMiddleware,
        slow_request_threshold=getattr(config, "slow_request_threshold", 2.0) if config else 2.0,
    )

    # Request/response logging
    app.add_middleware(
        RequestLoggingMiddleware,
        log_requests=True,
        log_responses=True,
        log_request_body=False,  # Disable in production for performance
        log_response_body=False,
        skip_paths=["/health", "/metrics", "/docs", "/openapi.json", "/favicon.ico"],
    )

    # Correlation ID tracking (last to be first in processing)
    app.add_middleware(CorrelationIDMiddleware)

    logger.info("API middleware configured successfully")

    return app
