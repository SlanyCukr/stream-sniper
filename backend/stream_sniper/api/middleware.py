"""
FastAPI middleware for Stream Sniper API.

This module provides middleware for correlation ID tracking and request/response
logging with per-request timing (the ``X-Process-Time`` header and slow-request
warnings). Endpoint metrics aggregation lives in ``api.py``'s
``metrics_middleware``, which owns the runtime metric/pool scopes.
"""

import time
import uuid

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from ..logging_config import correlation_context, get_logger

logger = get_logger(__name__)


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
    """Log HTTP requests/responses (bodies never logged) and time every request.

    Owns the single request-duration measurement: the ``X-Process-Time`` response
    header is set on every request (including skip paths), and completions slower
    than ``slow_request_threshold`` seconds are logged as warnings.
    """

    def __init__(
        self,
        app: ASGIApp,
        skip_paths: list[str] | None = None,
        slow_request_threshold: float = 2.0,
    ) -> None:
        super().__init__(app)
        self.skip_paths = skip_paths if skip_paths is not None else ["/health", "/metrics", "/docs", "/openapi.json"]
        self.slow_request_threshold = slow_request_threshold

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start_time = time.time()

        if request.url.path in self.skip_paths:
            response = await call_next(request)
            response.headers["X-Process-Time"] = str(round(time.time() - start_time, 3))
            return response

        self._log_request(request)

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

        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(round(process_time, 3))
        self._log_completed_response(request, response, process_time)
        return response

    def _log_request(self, request: Request) -> None:
        request_data: dict[str, object] = {
            "method": request.method,
            "url": str(request.url),
            "client_ip": self._get_client_ip(request),
            "user_agent": request.headers.get("user-agent", ""),
            "path": request.url.path,
            "query_params": dict(request.query_params),
        }
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
        elif process_time > self.slow_request_threshold:
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


def setup_middleware(app: FastAPI) -> FastAPI:
    """Set up all middleware for the FastAPI application."""

    app.add_middleware(
        RequestLoggingMiddleware,
        skip_paths=["/health", "/metrics", "/docs", "/openapi.json", "/favicon.ico"],
    )

    # Starlette applies the last-added middleware first.
    app.add_middleware(CorrelationIDMiddleware)

    logger.info("API middleware configured successfully")

    return app
