"""Streaming read gateway for full chat-log exports."""

from collections.abc import Iterator
from uuid import uuid4

from ...core.connection_pool import DatabaseConnectionPool, get_active_pool
from .records import MessageReplayRow

_EXPORT_SQL = """
    SELECT m.id, TO_CHAR(m.time, 'YYYY-MM-DD"T"HH24:MI:SS.US'), m.chatter_id, c.nick,
           mt.text, m.is_subscriber, m.badges
    FROM message m
    JOIN chatter c ON c.id = m.chatter_id
    JOIN message_text mt ON mt.id = m.message_text_id
    WHERE m.stream_id = %s
    ORDER BY m.time ASC, m.id ASC
"""


def iter_stream_message_export_db(
    stream_id: int,
    pool: DatabaseConnectionPool | None = None,
) -> Iterator[MessageReplayRow]:
    """Yield a stream's chat rows while owning the named cursor and read transaction."""
    resolved_pool = pool or get_active_pool()
    with resolved_pool.get_connection() as connection:
        cursor = connection.cursor(name=f"chat_export_{stream_id}_{uuid4().hex}")
        cursor.itersize = 5000
        try:
            cursor.execute(_EXPORT_SQL, (stream_id,))
            for row in cursor:
                yield MessageReplayRow(*row)
        finally:
            cursor.close()
            connection.rollback()
