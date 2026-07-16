"""One sanitized boundary for unexpected API exceptions."""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from ..logging_config import get_correlation_id, get_logger

logger = get_logger(__name__)


class UnexpectedExceptionMiddleware(BaseHTTPMiddleware):
    """Log unexpected failures with request context and hide internals from clients."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        try:
            return await call_next(request)
        except Exception:
            logger.exception(
                "Unhandled API exception",
                extra={
                    "http_method": request.method,
                    "http_path": request.url.path,
                    "correlation_id": get_correlation_id(),
                },
            )
            return JSONResponse(status_code=500, content={"detail": "Internal server error"})
