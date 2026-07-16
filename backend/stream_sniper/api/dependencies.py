"""Read-only FastAPI dependencies for application-owned runtime resources."""

from typing import cast

from fastapi import Request

from ..collector.twitch_api import TwitchAPI
from .caching.cache import InProcessCache
from .config import APIConfig
from .observability.health import HealthChecker
from .observability.monitoring import MetricsCollector


def get_config(request: Request) -> APIConfig:
    return cast(APIConfig, request.app.state.config)


def get_cache(request: Request) -> InProcessCache:
    return cast(InProcessCache, request.app.state.runtime.cache)


def get_metrics_collector(request: Request) -> MetricsCollector:
    return cast(MetricsCollector, request.app.state.runtime.metrics)


def get_health_checker(request: Request) -> HealthChecker:
    return cast(HealthChecker, request.app.state.runtime.health)


def get_twitch_client(request: Request) -> TwitchAPI:
    return cast(TwitchAPI, request.app.state.runtime.twitch)
