"""
Database connection pool management for improved performance and resource utilization.
"""
import os
import logging
import threading
from contextlib import contextmanager
from typing import Dict, Any, Optional

import psycopg2
from psycopg2 import pool
from dotenv import load_dotenv

logger = logging.getLogger(__name__)


class DatabaseConnectionPool:
    """
    Singleton connection pool manager for PostgreSQL database connections.
    Provides thread-safe connection pooling with health monitoring and error handling.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Ensure singleton pattern for connection pool."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseConnectionPool, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the connection pool if not already initialized."""
        if hasattr(self, '_initialized'):
            return
            
        self._initialized = True
        self._pool = None
        self._config = self._get_db_config()
        self._initialize_pool()
    
    def _get_db_config(self) -> Dict[str, Any]:
        """Load database configuration from environment variables."""
        load_dotenv()
        
        config = {
            'user': os.environ['USER'],
            'password': os.environ['PASSWORD'],
            'host': os.environ['HOST'],
            'database': os.environ['DATABASE'],
            'port': int(os.environ.get('PORT', 5432)),
            'options': '-c search_path=stream_sniper'
        }
        
        # Pool configuration with sensible defaults
        config.update({
            'minconn': int(os.environ.get('DB_POOL_MIN_CONN', 2)),
            'maxconn': int(os.environ.get('DB_POOL_MAX_CONN', 20)),
            'connect_timeout': int(os.environ.get('DB_CONNECT_TIMEOUT', 10)),
            'command_timeout': int(os.environ.get('DB_COMMAND_TIMEOUT', 60)),
        })
        
        return config
    
    def _initialize_pool(self):
        """Initialize the connection pool."""
        try:
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=self._config['minconn'],
                maxconn=self._config['maxconn'],
                user=self._config['user'],
                password=self._config['password'],
                host=self._config['host'],
                port=self._config['port'],
                database=self._config['database'],
                options=self._config['options'],
                connect_timeout=self._config['connect_timeout']
            )
            logger.info(f"Database connection pool initialized with {self._config['minconn']}-{self._config['maxconn']} connections")
        except Exception as e:
            logger.error(f"Failed to initialize database connection pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """
        Context manager to get a connection from the pool.
        Ensures connections are properly returned to the pool.
        
        Usage:
            with pool.get_connection() as conn:
                cursor = conn.cursor()
                # ... database operations
        """
        connection = None
        try:
            if self._pool is None:
                raise RuntimeError("Connection pool not initialized")
                
            connection = self._pool.getconn()
            if connection is None:
                raise RuntimeError("Unable to get connection from pool")
            
            # Test connection health
            if connection.closed:
                logger.warning("Retrieved closed connection, attempting to reconnect")
                self._pool.putconn(connection, close=True)
                connection = self._pool.getconn()
                if connection is None or connection.closed:
                    raise RuntimeError("Unable to get healthy connection from pool")
            
            yield connection
            
        except psycopg2.pool.PoolError as e:
            logger.error(f"Connection pool error: {e}")
            raise
        except psycopg2.Error as e:
            logger.error(f"Database connection error: {e}")
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            raise
        except Exception as e:
            logger.error(f"Unexpected error with database connection: {e}")
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            raise
        finally:
            if connection:
                try:
                    # Return connection to pool
                    self._pool.putconn(connection)
                except Exception as e:
                    logger.error(f"Error returning connection to pool: {e}")
    
    @contextmanager
    def get_cursor(self, commit: bool = False):
        """
        Context manager to get a cursor with automatic connection management.
        
        Args:
            commit: Whether to commit the transaction automatically
            
        Usage:
            with pool.get_cursor() as cursor:
                cursor.execute("SELECT * FROM table")
                result = cursor.fetchall()
        """
        with self.get_connection() as connection:
            cursor = None
            try:
                cursor = connection.cursor()
                yield cursor
                
                if commit:
                    connection.commit()
                    
            except Exception as e:
                connection.rollback()
                logger.error(f"Database operation failed: {e}")
                raise
            finally:
                if cursor:
                    cursor.close()
    
    def get_pool_status(self) -> Dict[str, Any]:
        """
        Get current pool status for monitoring.
        
        Returns:
            Dictionary with pool statistics
        """
        if self._pool is None:
            return {"status": "not_initialized"}
        
        # Note: psycopg2 ThreadedConnectionPool doesn't expose detailed stats
        # This is a basic implementation
        return {
            "status": "active",
            "minconn": self._config['minconn'],
            "maxconn": self._config['maxconn'],
            "config": {k: v for k, v in self._config.items() if k not in ['password']}
        }
    
    def close_all_connections(self):
        """Close all connections in the pool."""
        if self._pool:
            try:
                self._pool.closeall()
                logger.info("All database connections closed")
            except Exception as e:
                logger.error(f"Error closing connection pool: {e}")
            finally:
                self._pool = None
    
    def health_check(self) -> bool:
        """
        Perform a health check on the connection pool.
        
        Returns:
            True if pool is healthy, False otherwise
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result is not None and result[0] == 1
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# Global pool instance
_pool_instance: Optional[DatabaseConnectionPool] = None


def get_pool() -> DatabaseConnectionPool:
    """
    Get the global database connection pool instance.
    
    Returns:
        DatabaseConnectionPool instance
    """
    global _pool_instance
    if _pool_instance is None:
        _pool_instance = DatabaseConnectionPool()
    return _pool_instance


def close_pool():
    """Close the global connection pool."""
    global _pool_instance
    if _pool_instance:
        _pool_instance.close_all_connections()
        _pool_instance = None