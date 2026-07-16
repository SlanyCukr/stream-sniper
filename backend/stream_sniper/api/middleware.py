"""
FastAPI middleware for Stream Sniper API.

This module provides middleware for correlation ID tracking, request/response logging,
and performance monitoring.
"""

import time
import uuid

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from ..logging_config import correlation_context, get_logger
from .config import APIConfig

logger = get_logger(__name__)
MAX_LOGGED_RESPONSE_BYTES = 1_024


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation IDs for request tracing."""

    def __init__(self, app: ASGIApp, header_name: str = "X-Correlation-ID") -> None:
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        correlation_id = request.headers.get(self.header_name) or str(uuid.uuid4())

        with correlation_context(correlation_id):
            request.state.correlation_id = correlation_id
            response = await call_next(request)
            response.headers[self.header_name] = correlation_id

            return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""

    def __init__(
        self,
        app: ASGIApp,
        log_requests: bool = True,
        log_responses: bool = True,
        log_request_body: bool = False,
        log_response_body: bool = False,
        skip_paths: list[str] | None = None,
    ) -> None:
        super().__init__(app)
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_request_body = log_request_body
        self.log_response_body = log_response_body
        self.skip_paths = skip_paths if skip_paths is not None else ["/health", "/metrics", "/docs", "/openapi.json"]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()

        if request.url.path in self.skip_paths:
            return await call_next(request)

        if self.log_requests:
            await self._log_request(request)

        try:
            response = await call_next(request)
        except Exception as e:
            logger.error(
                "HTTP request failed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "process_time_seconds": round(time.time() - start_time, 3),
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                exc_info=True,
            )
            raise

        if self.log_responses:
            self._log_completed_response(request, response, time.time() - start_time)
        return response

    async def _log_request(self, request: Request) -> None:
        request_data: dict[str, object] = {
            "method": request.method,
            "url": str(request.url),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "path": request.url.path,
            "query_params": dict(request.query_params),
        }
        if self.log_request_body and request.method in {"POST", "PUT", "PATCH"}:
            try:
                body = await request.body()
                if len(body) < MAX_LOGGED_RESPONSE_BYTES:
                    request_data["body_size"] = len(body)
            except Exception as error:
                request_data["body_read_error"] = str(error)
        logger.info("HTTP request received", extra=request_data)

    def _log_completed_response(self, request: Request, response: Response, process_time: float) -> None:
        response_data: dict[str, object] = {
            "status_code": response.status_code,
            "process_time_seconds": round(process_time, 3),
            "method": request.method,
            "path": request.url.path,
        }
        if response.status_code >= 500:
            log_level = "error"
        elif response.status_code >= 400:
            log_level = "warning"
        elif process_time > 5.0:
            log_level = "warning"
            response_data["performance_warning"] = "slow_request"
        else:
            log_level = "info"
        getattr(logger, log_level)("HTTP request completed", extra=response_data)

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP address from request."""
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip

        if request.client is not None:
            return request.client.host

        return "unknown"


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring API performance."""

    def __init__(self, app: ASGIApp, slow_request_threshold: float = 2.0) -> None:
        super().__init__(app)
        self.slow_request_threshold = slow_request_threshold

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()

        try:
            response = await call_next(request)
            process_time = time.time() - start_time

            performance_data: dict[str, object] = {
                "endpoint": f"{request.method} {request.url.path}",
                "duration_seconds": round(process_time, 3),
                "status_code": response.status_code,
            }

            if process_time > self.slow_request_threshold:
                performance_data["performance_issue"] = "slow_request"
                logger.warning("Slow API request detected", extra=performance_data)
            else:
                logger.debug("API request performance", extra=performance_data)

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


def setup_middleware(app: FastAPI, config: APIConfig | None = None) -> FastAPI:
    """Set up all middleware for the FastAPI application."""

    app.add_middleware(
        PerformanceMonitoringMiddleware,
        slow_request_threshold=getattr(config, "slow_request_threshold", 2.0) if config else 2.0,
    )

    app.add_middleware(
        RequestLoggingMiddleware,
        log_requests=True,
        log_responses=True,
        log_request_body=False,  # Disable in production for performance
        log_response_body=False,
        skip_paths=["/health", "/metrics", "/docs", "/openapi.json", "/favicon.ico"],
    )

    # Starlette applies the last-added middleware first.
    app.add_middleware(CorrelationIDMiddleware)

    logger.info("API middleware configured successfully")

    return app
