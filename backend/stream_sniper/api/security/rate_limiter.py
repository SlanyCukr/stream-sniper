"""
Rate limiting implementation using slowapi (FastAPI-compatible version of Flask-Limiter).
Provides configurable rate limits backed by in-process memory storage.
"""

import logging
from collections.abc import Callable
from contextvars import ContextVar
from functools import wraps
from inspect import iscoroutinefunction, signature
from typing import Any, TypedDict
from weakref import WeakSet

from fastapi import FastAPI, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.responses import Response

from ..config import RateLimitConfig as AppRateLimitConfig

logger = logging.getLogger(__name__)
_request_rate_config: ContextVar[AppRateLimitConfig | None] = ContextVar("request_rate_config", default=None)


class AppLimiterRegistry:
    """Import-safe route policy registry backed by one Limiter per application."""

    def __init__(self) -> None:
        self._bindings: list[tuple[Any, Callable[..., Any]]] = []
        self._instances: WeakSet[Limiter] = WeakSet()

    @staticmethod
    def _request_from(args: tuple[Any, ...], kwargs: dict[str, Any], request_index: int) -> Request:
        request = kwargs.get("request", args[request_index] if len(args) > request_index else None)
        if not isinstance(request, Request):
            raise TypeError('parameter "request" must be a Starlette Request')
        return request

    @staticmethod
    def _enforce(request: Request, function: Callable[..., Any]) -> tuple[Limiter, bool]:
        app_limiter: Limiter = request.app.state.limiter
        checked_here = not getattr(request.state, "_rate_limiting_complete", False)
        if app_limiter.enabled and checked_here:
            app_limiter._check_request_limit(request, function, False)
            request.state._rate_limiting_complete = True
        return app_limiter, checked_here

    @staticmethod
    def _inject_headers(app_limiter: Limiter, request: Request, result: Any, kwargs: dict[str, Any]) -> None:
        if not app_limiter.enabled:
            return
        response = result if isinstance(result, Response) else kwargs.get("response")
        if not isinstance(response, Response):
            raise TypeError("rate-limited endpoints must return or declare a Response")
        app_limiter._inject_headers(response, request.state.view_rate_limit)

    def limit(self, limit_value: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Record a route policy and dispatch enforcement to the request's app."""

        def decorator(function: Callable[..., Any]) -> Callable[..., Any]:
            self._bindings.append((limit_value, function))
            for instance in self._instances:
                instance.limit(limit_value)(function)

            parameters = list(signature(function).parameters)
            try:
                request_index = parameters.index("request")
            except ValueError as exc:
                raise TypeError(f'{function.__name__} must declare a "request" parameter') from exc

            if iscoroutinefunction(function):

                @wraps(function)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    request = self._request_from(args, kwargs, request_index)
                    app_limiter, checked_here = self._enforce(request, function)
                    result = await function(*args, **kwargs)
                    if checked_here:
                        self._inject_headers(app_limiter, request, result, kwargs)
                    return result

                return async_wrapper

            @wraps(function)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                request = self._request_from(args, kwargs, request_index)
                app_limiter, checked_here = self._enforce(request, function)
                result = function(*args, **kwargs)
                if checked_here:
                    self._inject_headers(app_limiter, request, result, kwargs)
                return result

            return sync_wrapper

        return decorator

    def bind(self, instance: Limiter) -> None:
        """Copy recorded policies into a newly-created application limiter."""
        for limit_value, function in self._bindings:
            instance.limit(limit_value)(function)
        self._instances.add(instance)

    def reset(self) -> None:
        """Reset every bound application limiter (primarily for test isolation)."""
        for instance in self._instances:
            instance.reset()


def bind_rate_config_and_get_identifier(request: Request) -> str:
    """Bind the app-owned request policy and return the client IP key."""
    app = request.scope.get("app")
    if app is not None and hasattr(app.state, "rate_limit_config"):
        _request_rate_config.set(app.state.rate_limit_config)
    client_ip = get_remote_address(request)
    return f"ip:{client_ip}"


def create_limiter(config: AppRateLimitConfig | None = None) -> Limiter:
    """Create a single-process limiter whose counters reset on restart."""
    resolved = config or AppRateLimitConfig()
    limiter = Limiter(
        key_func=bind_rate_config_and_get_identifier,
        storage_uri="memory://",
        default_limits=[resolved.default_limit],
        strategy=resolved.strategy,
        headers_enabled=resolved.headers_enabled,
        enabled=resolved.enabled,
    )

    logger.info("Rate limiter initialized with in-memory storage")
    return limiter


# Decorators bind policy metadata here; counters and configuration remain app-owned.
limiter = AppLimiterRegistry()


class EndpointRateLimits:
    """Request-time rate providers safe to bind during normal module imports."""

    @staticmethod
    def _value(field: str) -> str:
        config = _request_rate_config.get()
        if config is None:
            raise RuntimeError("Rate-limit configuration is not bound to the current request")
        if not config.enabled:
            return "1000000000 per day"
        return str(getattr(config, field))

    GENERAL = staticmethod(lambda key: EndpointRateLimits._value("general"))
    ANALYTICS = staticmethod(lambda key: EndpointRateLimits._value("analytics"))
    HEAVY = staticmethod(lambda key: EndpointRateLimits._value("heavy"))
    HEALTH = staticmethod(lambda key: EndpointRateLimits._value("health"))
    BULK = staticmethod(lambda key: EndpointRateLimits._value("bulk"))
    SEARCH = staticmethod(lambda key: EndpointRateLimits._value("search"))


# Global rate limit configuration
rate_limits = EndpointRateLimits()


class RateLimitStoragePayload(TypedDict):
    type: str
    status: str


class RateLimitPolicyPayload(TypedDict):
    general: str
    analytics: str
    heavy: str
    health: str
    bulk: str
    search: str


class RateLimitStatsPayload(TypedDict):
    enabled: bool
    storage: RateLimitStoragePayload
    default_limits: list[str]
    strategy: str
    headers_enabled: bool
    rate_limits: RateLimitPolicyPayload


def get_rate_limit_stats(config: AppRateLimitConfig) -> RateLimitStatsPayload:
    """Return the active in-process rate-limit policy and storage health."""
    return {
        "enabled": config.enabled,
        "storage": {"type": "memory", "status": "healthy"},
        "default_limits": [config.default_limit],
        "strategy": config.strategy,
        "headers_enabled": config.headers_enabled,
        "rate_limits": {
            "general": config.general,
            "analytics": config.analytics,
            "heavy": config.heavy,
            "health": config.health,
            "bulk": config.bulk,
            "search": config.search,
        },
    }


def custom_rate_limit_handler(request: Request, exc: Exception) -> Response:
    """Return SlowAPI's supported JSON 429 response with limit headers."""
    if not isinstance(exc, RateLimitExceeded):
        raise TypeError("Rate-limit handler received an unexpected exception")
    return _rate_limit_exceeded_handler(request, exc)


def setup_rate_limiting(app: FastAPI, config: AppRateLimitConfig | None = None) -> None:
    """Bind one limiter, middleware, and 429 handler to the application."""
    resolved = config or AppRateLimitConfig()
    app_limiter = create_limiter(resolved)
    limiter.bind(app_limiter)
    app.state.limiter = app_limiter
    app.state.rate_limit_config = resolved
    app.add_middleware(SlowAPIMiddleware)

    app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

    logger.info("Rate limiting middleware configured successfully")
