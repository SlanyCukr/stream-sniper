"""
Database connection pool management for improved performance and resource utilization.
"""

import logging
import os
from collections.abc import Callable, Coroutine, Iterator, Mapping
from contextlib import contextmanager, suppress
from contextvars import ContextVar, Token
from dataclasses import dataclass
from functools import wraps
from typing import Any, NotRequired, TypedDict

import psycopg2
import psycopg2.pool  # noqa: F401  # imported for side effect: registers psycopg2.pool submodule
from dotenv import load_dotenv
from psycopg2.extensions import connection as PsycopgConnection
from psycopg2.extensions import cursor as PsycopgCursor

logger = logging.getLogger(__name__)


class PoolConfigPayload(TypedDict):
    user: str
    host: str
    database: str
    port: int
    options: str
    connect_timeout: int
    command_timeout: int


class PoolStatusPayload(TypedDict):
    status: str
    minconn: NotRequired[int]
    maxconn: NotRequired[int]
    config: NotRequired[PoolConfigPayload]


@dataclass(frozen=True)
class DatabasePoolConfig:
    """Single owner of the POSTGRES_* / DB_* database-connection contract.

    Every runtime (API, CLI commands, services) composes this type; nothing else
    re-declares these fields or their defaults. Credentials default to empty and
    are validated by ``DatabaseConnectionPool.open()``.
    """

    user: str = ""
    password: str = ""
    host: str = "localhost"
    database: str = ""
    port: int = 5432
    options: str = "-c search_path=stream_sniper"
    minconn: int = 2
    maxconn: int = 20
    connect_timeout: int = 10
    command_timeout: int = 60


def load_database_pool_config(environ: Mapping[str, str] | None = None, *, require: bool = True) -> DatabasePoolConfig:
    """Build a pool configuration at an executable composition boundary.

    With ``require=True`` (CLI/service entry points) missing credentials raise
    immediately. With ``require=False`` (API config snapshot) they stay empty
    and are validated later by ``DatabaseConnectionPool.open()``.
    """
    env = os.environ if environ is None else environ

    def credential(name: str) -> str:
        value = env.get(name, "")
        if require and not value:
            raise RuntimeError(f"Database configuration missing: set {name} in the environment")
        return value

    return DatabasePoolConfig(
        user=credential("POSTGRES_USER"),
        password=credential("POSTGRES_PASSWORD"),
        # With require=True, credential() raises before the fallback can fire; the
        # "localhost" default only applies on the lenient (require=False) path.
        host=credential("POSTGRES_HOST") or "localhost",
        database=credential("POSTGRES_DB"),
        port=int(env.get("POSTGRES_PORT", "5432")),
        minconn=int(env.get("DB_POOL_MIN_CONN", "2")),
        maxconn=int(env.get("DB_POOL_MAX_CONN", "20")),
        connect_timeout=int(env.get("DB_CONNECT_TIMEOUT", "10")),
        command_timeout=int(env.get("DB_COMMAND_TIMEOUT", "60")),
    )


class DatabaseConnectionPool:
    """
    PostgreSQL connection pool manager.
    Provides thread-safe connection pooling with health monitoring and error handling.
    """

    def __init__(self, config: DatabasePoolConfig) -> None:
        """Create one independently owned pool manager from explicit settings."""
        self._pool: psycopg2.pool.ThreadedConnectionPool | None = None
        self._config = config

    def open(self) -> None:
        """Open physical connections once, at the owning runtime's startup boundary."""
        if self._pool is not None:
            return
        if not all((self._config.user, self._config.password, self._config.host, self._config.database)):
            raise RuntimeError("Database pool configuration requires user, password, host, and database")
        self._initialize_pool()

    def _initialize_pool(self) -> None:
        """Initialize the connection pool."""
        try:
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=self._config.minconn,
                maxconn=self._config.maxconn,
                user=self._config.user,
                password=self._config.password,
                host=self._config.host,
                port=self._config.port,
                database=self._config.database,
                options=self._config.options,
                connect_timeout=self._config.connect_timeout,
            )
            logger.info(
                "Database connection pool initialized with %s-%s connections",
                self._config.minconn,
                self._config.maxconn,
            )
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise

    @contextmanager
    def get_connection(self) -> Iterator[PsycopgConnection]:
        """Check out a connection and always return it to the pool."""
        connection = None
        operation_failed = False
        try:
            connection = self._checkout_connection()
            yield connection
        except psycopg2.pool.PoolError as e:
            operation_failed = True
            logger.error(f"Connection pool error: {e}")
            raise
        except psycopg2.Error as e:
            operation_failed = True
            logger.error(f"Database connection error: {e}")
            self._rollback_connection(connection)
            raise
        except Exception as e:
            operation_failed = True
            logger.error(f"Unexpected error with database connection: {e}")
            self._rollback_connection(connection)
            raise
        finally:
            if connection:
                self._return_connection(connection, operation_failed)

    def _checkout_connection(self) -> PsycopgConnection:
        if self._pool is None:
            raise RuntimeError("Connection pool not initialized")
        connection = self._pool.getconn()
        if connection is None:
            raise RuntimeError("Unable to get connection from pool")
        if not connection.closed:
            return connection

        logger.warning("Retrieved closed connection, attempting to reconnect")
        self._pool.putconn(connection, close=True)
        replacement = self._pool.getconn()
        if replacement is None or replacement.closed:
            raise RuntimeError("Unable to get healthy connection from pool")
        return replacement

    @staticmethod
    def _rollback_connection(connection: PsycopgConnection | None) -> None:
        if connection:
            with suppress(Exception):
                connection.rollback()

    def _return_connection(self, connection: PsycopgConnection, operation_failed: bool) -> None:
        if self._pool is None:
            connection.close()
            if not operation_failed:
                raise RuntimeError("Connection pool closed before connection could be returned")
            return
        try:
            self._pool.putconn(connection)
        except Exception as error:
            logger.exception("Error returning connection to pool")
            with suppress(Exception):
                connection.close()
            if not operation_failed:
                raise RuntimeError("Failed to return database connection to pool") from error

    @contextmanager
    def get_cursor(self, commit: bool = False) -> Iterator[PsycopgCursor]:
        """Manage one cursor and optionally commit after its body succeeds."""
        with self.get_connection() as connection:
            cursor = None
            try:
                cursor = connection.cursor()
                yield cursor

                if commit:
                    connection.commit()
            finally:
                if cursor:
                    cursor.close()

    def get_pool_status(self) -> PoolStatusPayload:
        """Return connection configuration safe for operational monitoring."""
        if self._pool is None:
            return {"status": "not_initialized"}

        # Note: psycopg2 ThreadedConnectionPool doesn't expose detailed stats
        # This is a basic implementation
        return {
            "status": "active",
            "minconn": self._config.minconn,
            "maxconn": self._config.maxconn,
            "config": {
                "user": self._config.user,
                "host": self._config.host,
                "database": self._config.database,
                "port": self._config.port,
                "options": self._config.options,
                "connect_timeout": self._config.connect_timeout,
                "command_timeout": self._config.command_timeout,
            },
        }

    def close_all_connections(self) -> None:
        """Close all connections in the pool."""
        if self._pool:
            try:
                self._pool.closeall()
                logger.info("All database connections closed")
            except Exception as e:
                logger.exception("Error closing connection pool")
                raise RuntimeError("Failed to close database connection pool") from e
            finally:
                self._pool = None

    def health_check(self) -> bool:
        """Check that the pool can execute a trivial query."""
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result is not None and result[0] == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


_active_pool: ContextVar[DatabaseConnectionPool | None] = ContextVar("database_pool", default=None)


def enter_pool_scope(pool: DatabaseConnectionPool) -> Token[DatabaseConnectionPool | None]:
    return _active_pool.set(pool)


def exit_pool_scope(token: Token[DatabaseConnectionPool | None]) -> None:
    _active_pool.reset(token)


def get_active_pool() -> DatabaseConnectionPool:
    """Return the pool owned by the current runtime scope."""
    active = _active_pool.get()
    if active is None:
        raise RuntimeError("No database pool is bound to the current runtime")
    return active


def peek_active_pool() -> DatabaseConnectionPool | None:
    """Return the currently bound pool, or None when the scope is unbound.

    For components that capture the pool at construction time so they can re-bind
    it on threads whose context never saw the entrypoint's binding (ContextVars do
    not cross thread boundaries — e.g. third-party callback threads).
    """
    return _active_pool.get()


@contextmanager
def database_runtime(config: DatabasePoolConfig | None = None) -> Iterator[DatabaseConnectionPool]:
    """Own one explicitly configured pool for a command or service lifetime."""
    pool = DatabaseConnectionPool(config or load_database_pool_config())
    pool.open()
    token = enter_pool_scope(pool)
    try:
        yield pool
    finally:
        exit_pool_scope(token)
        pool.close_all_connections()


def database_entrypoint[**P, R](function: Callable[P, R]) -> Callable[P, R]:
    """Wrap a synchronous command in an explicitly owned database runtime."""

    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        load_dotenv()
        with database_runtime():
            return function(*args, **kwargs)

    return wrapped


def async_database_entrypoint[**P, R](
    function: Callable[P, Coroutine[Any, Any, R]],
) -> Callable[P, Coroutine[Any, Any, R]]:
    """Wrap an asynchronous service in an explicitly owned database runtime."""

    @wraps(function)
    async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        load_dotenv()
        with database_runtime():
            return await function(*args, **kwargs)

    return wrapped
