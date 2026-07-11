import logging
from functools import wraps

from .connection_pool import get_pool

logger = logging.getLogger(__name__)


def get_db_config():
    """
    Legacy function for backward compatibility.
    Database configuration is now handled by the connection pool.
    """
    pool = get_pool()
    return pool._config


def with_cursor_connection(f):
    """
    Decorator for database operations that need both cursor and connection access.
    Uses connection pooling for improved performance and resource management.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        pool = get_pool()

        with pool.get_connection() as connection:
            cursor = None
            try:
                cursor = connection.cursor()
                values = f(*args, cursor, connection, **kwargs)
                return values
            except Exception as e:
                logger.error(f"Database operation failed in {f.__name__}: {e}")
                raise
            finally:
                if cursor:
                    cursor.close()

    return wrapper


def with_cursor(f):
    """
    Decorator for read-only database operations that only need cursor access.
    Uses connection pooling for improved performance and resource management.
    """

    @wraps(f)
    def wrapper(*args, **kwargs):
        pool = get_pool()

        with pool.get_cursor() as cursor:
            try:
                values = f(*args, cursor, **kwargs)
                return values
            except Exception as e:
                logger.error(f"Database operation failed in {f.__name__}: {e}")
                raise

    return wrapper


def log_database_operation(f):
    """
    Decorator to log database operations for monitoring and debugging.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        operation_name = f.__name__
        logger.debug(f"Starting database operation: {operation_name}")
        try:
            result = f(*args, **kwargs)
            logger.debug(f"Database operation completed successfully: {operation_name}")
            return result
        except Exception as e:
            logger.error(f"Database operation failed: {operation_name} - {e}")
            raise
    return wrapper
