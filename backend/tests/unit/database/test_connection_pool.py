"""Lifecycle tests for explicitly owned database pools."""

from unittest.mock import Mock

import pytest

from stream_sniper.database.core import connection_pool


def test_active_pool_requires_an_owning_runtime() -> None:
    with pytest.raises(RuntimeError, match="No database pool is bound"):
        connection_pool.get_active_pool()


def test_database_config_uses_one_postgres_environment_contract() -> None:
    values = {
        "POSTGRES_USER": "app_user",
        "POSTGRES_PASSWORD": "secret",
        "POSTGRES_HOST": "database",
        "POSTGRES_DB": "stream_sniper",
        "POSTGRES_PORT": "5544",
    }
    config = connection_pool.load_database_pool_config(values)

    assert config.user == "app_user"
    assert config.password == "secret"
    assert config.host == "database"
    assert config.database == "stream_sniper"
    assert config.port == 5544


def test_explicit_pool_configuration_opens_only_when_requested(monkeypatch: pytest.MonkeyPatch) -> None:
    threaded_pool = Mock()
    constructor = Mock(return_value=threaded_pool)
    monkeypatch.setattr(connection_pool.psycopg2.pool, "ThreadedConnectionPool", constructor)
    config = connection_pool.DatabasePoolConfig(
        "runtime-user",
        "runtime-secret",
        "runtime-host",
        "runtime-database",
        minconn=3,
        maxconn=7,
    )

    pool = connection_pool.DatabaseConnectionPool(config)
    constructor.assert_not_called()

    pool.open()
    pool.open()

    constructor.assert_called_once_with(
        minconn=3,
        maxconn=7,
        user="runtime-user",
        password="runtime-secret",
        host="runtime-host",
        port=5432,
        database="runtime-database",
        options="-c search_path=stream_sniper",
        connect_timeout=10,
    )


def test_active_runtime_pool_is_resolved_from_scope() -> None:
    runtime_pool = Mock()
    token = connection_pool.enter_pool_scope(runtime_pool)
    try:
        assert connection_pool.get_active_pool() is runtime_pool
    finally:
        connection_pool.exit_pool_scope(token)
