import logging
from typing import Callable

from ..database.connection_pool import get_pool

logger = logging.getLogger(__name__)


def get_db_config():
    """
    Legacy function for backward compatibility.
    Database configuration is now handled by the connection pool.
    """
    pool = get_pool()
    return pool._config


class DatabaseBuffer:
    """
    Database buffer for batch operations using connection pooling.
    Improved version that uses connection pool instead of maintaining a single connection.
    """
    
    def __init__(self, f: Callable, buffer_len: int = 7500):
        self.f = f
        self.buffer_len = buffer_len
        self.items = []
        self.pool = get_pool()
        
        logger.info(f"DatabaseBuffer initialized with buffer length: {buffer_len}")

    def call_db_function(self):
        """Execute the buffered database function with current items."""
        # don't continue, if there are no items to be inserted
        if not self.items:
            return

        try:
            with self.pool.get_connection() as connection:
                cursor = None
                try:
                    cursor = connection.cursor()
                    self.f(self.items, cursor, connection)
                    connection.commit()
                    logger.debug(f"Successfully processed {len(self.items)} items")
                except Exception as e:
                    connection.rollback()
                    logger.error(f"Database buffer operation failed: {e}")
                    raise
                finally:
                    if cursor:
                        cursor.close()
                    self.items.clear()
        except Exception as e:
            logger.error(f"Failed to get database connection for buffer operation: {e}")
            # Clear items to prevent infinite retry loop
            self.items.clear()
            raise

    def add_item(self, item: tuple):
        """Add an item to the buffer and process if buffer is full."""
        self.items.append(item)

        if len(self.items) >= self.buffer_len:
            self.call_db_function()
    
    def flush(self):
        """Force flush any remaining items in the buffer."""
        if self.items:
            logger.info(f"Flushing {len(self.items)} remaining items from buffer")
            self.call_db_function()
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - ensure buffer is flushed."""
        self.flush()