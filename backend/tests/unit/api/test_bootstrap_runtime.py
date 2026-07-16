"""Tests for configuration, import, app-factory, and runtime ownership boundaries."""

import asyncio
import os
import subprocess
import sys
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.config import APIConfig, AuthConfig, CacheConfig, MonitoringConfig, RateLimitConfig, load_config
from stream_sniper.api.error_boundary import UnexpectedExceptionMiddleware
from stream_sniper.api.runtime import Runtime
from stream_sniper.database.core.connection_pool import get_active_pool


def _config(**kwargs: Any) -> APIConfig:
    return APIConfig(auth=AuthConfig(secret_key="test-secret"), **kwargs)


def test_load_config_returns_fresh_environment_snapshots() -> None:
    first = load_config(
        {
            "JWT_SECRET_KEY": "one",
            "API_PORT": "5002",
            "CACHE_ENABLED": "true",
            "POSTGRES_USER": "first-user",
            "POSTGRES_PASSWORD": "first-secret",
            "POSTGRES_HOST": "first-host",
            "POSTGRES_DB": "first-database",
        }
    )
    second = load_config(
        {
            "JWT_SECRET_KEY": "two",
            "API_PORT": "9000",
            "CACHE_ENABLED": "false",
            "POSTGRES_USER": "second-user",
            "POSTGRES_PASSWORD": "second-secret",
            "POSTGRES_HOST": "second-host",
            "POSTGRES_DB": "second-database",
        }
    )

    assert first.port == 5002
    assert first.cache.enabled is True
    assert first.auth.secret_key == "one"
    assert second.port == 9000
    assert second.cache.enabled is False
    assert second.auth.secret_key == "two"
    assert first.database.user == "first-user"
    assert second.database.host == "second-host"


@pytest.mark.parametrize("module", ["stream_sniper.api.caching.cache", "stream_sniper.api.security.auth"])
def test_api_submodule_import_does_not_construct_application(module: str) -> None:
    env = os.environ.copy()
    env.pop("JWT_SECRET_KEY", None)
    env.pop("SECRET_KEY", None)
    script = f"import sys; import {module}; assert 'stream_sniper.api.api' not in sys.modules"

    completed = subprocess.run([sys.executable, "-c", script], env=env, check=False, capture_output=True, text=True)

    assert completed.returncode == 0, completed.stderr


def test_create_app_uses_supplied_config_and_runtime() -> None:
    from stream_sniper.api.api import create_app

    class FakeRuntime:
        database = object()

        async def startup(self) -> None:
            pass

        async def close(self) -> None:
            pass

    config = _config(title="Factory App", port=6123, cache=CacheConfig(warm_on_startup=False))
    runtime = FakeRuntime()

    app = create_app(config, runtime_factory=lambda _: runtime)  # type: ignore[arg-type, return-value]

    assert app.title == "Factory App"
    assert app.state.config is config
    assert app.state.runtime is runtime
    assert app.servers == []


def test_api_request_scope_resolves_its_runtime_database_pool() -> None:
    from stream_sniper.api.api import create_app

    class FakeRuntime:
        def __init__(self) -> None:
            self.database = object()
            self.metrics = object()

        async def startup(self) -> None:
            pass

        async def close(self) -> None:
            pass

    runtime = FakeRuntime()
    app = create_app(
        _config(
            cache=CacheConfig(warm_on_startup=False),
            monitoring=MonitoringConfig(collect_request_metrics=False),
        ),
        runtime_factory=lambda _: runtime,  # type: ignore[arg-type, return-value]
    )

    @app.get("/runtime-pool")
    def runtime_pool() -> dict[str, bool]:
        return {"bound": get_active_pool() is runtime.database}

    with TestClient(app) as client:
        response = client.get("/runtime-pool")

    assert response.json() == {"bound": True}


def test_app_factory_constructs_isolated_rate_limiters() -> None:
    from stream_sniper.api.api import create_app

    first = create_app(_config(rate_limit=RateLimitConfig(default_limit="7 per minute")))
    second = create_app(_config(rate_limit=RateLimitConfig(default_limit="9 per minute")))

    assert first.state.limiter is not second.state.limiter
    assert first.state.limiter._storage is not second.state.limiter._storage
    assert str(next(iter(first.state.limiter._default_limits[0])).limit) == "7 per 1 minute"
    assert str(next(iter(second.state.limiter._default_limits[0])).limit) == "9 per 1 minute"


def test_unexpected_exception_boundary_logs_traceback_and_sanitizes(caplog: pytest.LogCaptureFixture) -> None:
    app = FastAPI()
    app.add_middleware(UnexpectedExceptionMiddleware)

    @app.get("/explode")
    def explode() -> None:
        raise RuntimeError("private database detail")

    with TestClient(app) as client:
        response = client.get("/explode")

    assert response.status_code == 500
    assert response.json() == {"detail": "Internal server error"}
    assert "private database detail" not in response.text
    record = next(record for record in caplog.records if record.message == "Unhandled API exception")
    record_data: Any = record
    assert record.exc_info is not None
    assert record_data.http_method == "GET"
    assert record_data.http_path == "/explode"


class FakeScheduler:
    def __init__(self) -> None:
        self.running = False
        self.starts = 0
        self.stops = 0
        self._stop = asyncio.Event()

    async def start(self) -> None:
        self.starts += 1
        self.running = True
        self._stop = asyncio.Event()
        await self._stop.wait()
        self.running = False

    async def stop(self) -> None:
        self.stops += 1
        self.running = False
        self._stop.set()

    def is_running(self) -> bool:
        return self.running


class FakeHealth:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class FakeTwitch:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


class FakeCache:
    def __init__(self) -> None:
        self.flushed = False

    def flush_all(self) -> bool:
        self.flushed = True
        return True


class FakeDatabase:
    def __init__(self) -> None:
        self.opened = False
        self.closed = False

    def open(self) -> None:
        self.opened = True

    def close_all_connections(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_runtime_defaults_are_isolated_per_application() -> None:
    first = Runtime(_config(cache=CacheConfig(warm_on_startup=False)))
    second = Runtime(_config(cache=CacheConfig(warm_on_startup=False)))

    assert first.cache is not second.cache
    assert first.metrics is not second.metrics
    assert first.health is not second.health
    assert first.twitch is not second.twitch
    assert first.database is not second.database

    await first.close()
    await second.close()


@pytest.mark.asyncio
async def test_runtime_opens_and_closes_its_own_database_pool() -> None:
    first_database = FakeDatabase()
    second_database = FakeDatabase()
    first = Runtime(
        _config(cache=CacheConfig(warm_on_startup=False)),
        database=first_database,  # type: ignore[arg-type]
    )
    second = Runtime(
        _config(cache=CacheConfig(warm_on_startup=False)),
        database=second_database,  # type: ignore[arg-type]
    )

    await first.startup()
    await second.startup()
    await first.close()

    assert first_database.opened is True
    assert first_database.closed is True
    assert second_database.opened is True
    assert second_database.closed is False

    await second.close()
    assert second_database.closed is True


@pytest.mark.asyncio
async def test_runtime_attempts_every_cleanup_and_raises_named_failures(caplog) -> None:
    calls: list[str] = []

    class FailingHealth(FakeHealth):
        def close(self) -> None:
            calls.append("health")
            raise RuntimeError("session stuck")

    class RecordingTwitch(FakeTwitch):
        async def close(self) -> None:
            calls.append("twitch")

    class RecordingCache:
        def flush_all(self) -> bool:
            calls.append("cache")
            return True

    runtime = Runtime(
        _config(cache=CacheConfig(warm_on_startup=False)),
        cache=RecordingCache(),  # type: ignore[arg-type]
        metrics=object(),  # type: ignore[arg-type]
        health=FailingHealth(),  # type: ignore[arg-type]
        twitch=RecordingTwitch(),  # type: ignore[arg-type]
    )

    with pytest.raises(ExceptionGroup) as raised:
        await runtime.close()

    assert calls == ["health", "twitch", "cache"]
    assert [str(error) for error in raised.value.exceptions] == ["health checker cleanup failed"]
    assert [record.resource for record in caplog.records if record.message == "Runtime cleanup failed"] == [
        "health checker",
    ]


@pytest.mark.asyncio
async def test_runtime_owns_cache_warm_failure_boundary(monkeypatch: pytest.MonkeyPatch, caplog) -> None:
    cache = object()
    calls: list[object] = []

    def failing_warm_cache(received_cache: object) -> None:
        calls.append(received_cache)
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("stream_sniper.api.runtime.warm_cache", failing_warm_cache)
    runtime = Runtime(
        _config(cache=CacheConfig(warm_on_startup=True)),
        cache=cache,  # type: ignore[arg-type]
        metrics=object(),  # type: ignore[arg-type]
        health=FakeHealth(),  # type: ignore[arg-type]
        twitch=FakeTwitch(),  # type: ignore[arg-type]
        database=FakeDatabase(),  # type: ignore[arg-type]
    )

    await runtime.startup()

    assert calls == [cache]
    assert [record.message for record in caplog.records].count("Cache warming failed") == 1
    assert "Cache warming completed" not in [record.message for record in caplog.records]
