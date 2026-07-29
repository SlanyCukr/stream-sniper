import logging
from collections.abc import Callable
from typing import Self

from psycopg2.extensions import connection as Connection
from psycopg2.extensions import cursor as Cursor

from ...database.core.connection_pool import get_active_pool

logger = logging.getLogger(__name__)


class DatabaseBuffer[RowT]:
    """Batches typed rows and flushes them through one persist callback.

    Generic over the row type so a buffer built on a typed gateway insert (e.g.
    ``insert_message_db`` taking ``MessageInsertRow``) keeps that contract —
    ``add_item`` only accepts the rows the callback can persist.
    """

    def __init__(
        self,
        persist_batch: Callable[[list[RowT], Cursor, Connection], None],
        buffer_len: int = 7500,
    ) -> None:
        self.persist_batch = persist_batch
        self.buffer_len = buffer_len
        self.items: list[RowT] = []
        self.pool = get_active_pool()

    def flush(self) -> int:
        """Persist one snapshot of pending rows, retaining them on any failure."""
        if not self.items:
            return 0

        pending = list(self.items)
        with self.pool.get_connection() as connection:
            cursor = None
            try:
                cursor = connection.cursor()
                self.persist_batch(pending, cursor, connection)
                connection.commit()
                logger.debug(f"Successfully processed {len(pending)} items")
            except Exception:
                connection.rollback()
                raise
            finally:
                if cursor:
                    cursor.close()
        del self.items[: len(pending)]
        return len(pending)

    def add_item(self, item: RowT) -> None:
        self.items.append(item)

        if len(self.items) >= self.buffer_len:
            self.flush()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        self.flush()
