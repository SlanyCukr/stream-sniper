import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from functools import wraps
from inspect import Signature, signature
from typing import Any, Concatenate, cast

from psycopg2.extensions import connection as Connection
from psycopg2.extensions import cursor as Cursor

from .connection_pool import get_active_pool

logger = logging.getLogger(__name__)


def _hide_injected_parameters(wrapper: Callable[..., Any], function: Callable[..., Any], names: set[str]) -> None:
    """Expose the caller-facing signature instead of decorator-injected args."""
    public = [parameter for parameter in signature(function).parameters.values() if parameter.name not in names]
    cast(Any, wrapper).__signature__ = Signature(
        parameters=public, return_annotation=signature(function).return_annotation
    )


@contextmanager
def read_cursor() -> Iterator[Cursor]:
    """Yield a read cursor for CRUD modules that also expose explicit writes."""
    with get_active_pool().get_cursor() as cursor:
        yield cursor


@contextmanager
def write_cursor() -> Iterator[Cursor]:
    """Make a CRUD module's commit boundary explicit beside its mutations."""
    with get_active_pool().get_cursor(commit=True) as cursor:
        yield cursor


def with_cursor_connection[**P, R](
    f: Callable[Concatenate[Cursor, Connection, P], R],
) -> Callable[P, R]:
    """
    Decorator for database operations that need both cursor and connection access.
    Uses connection pooling for improved performance and resource management.
    """

    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        pool = get_active_pool()

        with pool.get_connection() as connection:
            cursor = None
            try:
                cursor = connection.cursor()
                values = f(cursor, connection, *args, **kwargs)
                return values
            finally:
                if cursor:
                    cursor.close()

    _hide_injected_parameters(wrapper, f, {"cursor", "connection"})
    return wrapper


def with_cursor[**P, R](f: Callable[Concatenate[Cursor, P], R]) -> Callable[P, R]:
    """Inject a pooled cursor into a read-only gateway operation."""

    @wraps(f)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        with read_cursor() as cursor:
            return f(cursor, *args, **kwargs)

    _hide_injected_parameters(wrapper, f, {"cursor"})
    return wrapper
