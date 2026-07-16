"""Application-owned runtime resources and lifecycle transitions."""

import asyncio
from collections.abc import Awaitable, Callable
from inspect import isawaitable

from ..collector.twitch_api import TwitchAPI
from ..database.core.connection_pool import (
    DatabaseConnectionPool,
    DatabasePoolConfig,
    enter_pool_scope,
    exit_pool_scope,
)
from ..logging_config import get_logger
from .caching.cache import InProcessCache
from .caching.cache_warmup import warm_cache
from .config import APIConfig
from .observability.health import HealthChecker
from .observability.monitoring import MetricsCollector

logger = get_logger(__name__)


class Runtime:
    """Own process resources created for one FastAPI application lifespan."""

    def __init__(
        self,
        config: APIConfig,
        *,
        cache: InProcessCache | None = None,
        metrics: MetricsCollector | None = None,
        health: HealthChecker | None = None,
        twitch: TwitchAPI | None = None,
        database: DatabaseConnectionPool | None = None,
    ) -> None:
        self.config = config
        self.cache = cache or InProcessCache()
        self.metrics = metrics or MetricsCollector(config.monitoring.metrics_retention_hours)
        self.health = health or HealthChecker(config=config, cache=self.cache)
        self.twitch = twitch or TwitchAPI()
        self.database = database or DatabaseConnectionPool(
            DatabasePoolConfig(
                user=config.database.user,
                password=config.database.password,
                host=config.database.host,
                database=config.database.database,
                port=config.database.port,
                options=config.database.options,
                minconn=config.database.pool_min_conn,
                maxconn=config.database.pool_max_conn,
                connect_timeout=config.database.connect_timeout,
                command_timeout=config.database.command_timeout,
            )
        )

    async def startup(self) -> None:
        """Warm configured caches after the event loop is ready."""
        self.database.open()
        token = enter_pool_scope(self.database)
        try:
            if self.config.cache.enabled and self.config.cache.warm_on_startup:
                try:
                    await asyncio.to_thread(warm_cache, self.cache)
                    logger.info("Cache warming completed")
                except Exception:
                    logger.exception("Cache warming failed")
        finally:
            exit_pool_scope(token)

    async def close(self) -> None:
        """Attempt every owned cleanup and expose an aggregate shutdown outcome."""
        failures: list[Exception] = []
        cleanups: tuple[tuple[str, Callable[[], object | Awaitable[object]]], ...] = (
            ("health checker", self.health.close),
            ("Twitch client", self.twitch.close),
            ("cache", self.cache.flush_all),
            ("database pool", self.database.close_all_connections),
        )

        for resource, cleanup in cleanups:
            try:
                result = cleanup()
                if isawaitable(result):
                    await result
            except Exception as exc:
                logger.exception("Runtime cleanup failed", extra={"resource": resource})
                failure = RuntimeError(f"{resource} cleanup failed")
                failure.__cause__ = exc
                failures.append(failure)

        if failures:
            raise ExceptionGroup("Runtime shutdown failed", failures)
