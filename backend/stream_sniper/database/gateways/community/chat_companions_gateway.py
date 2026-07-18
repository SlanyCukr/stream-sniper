"""Database gateway for a chatter's top "chat companions" (co-attendance ranking).

Self-joins stream_chatter_stats on stream_id to find other chatters who shared streams
with the given chatter, keyed by the stream_chatter_stats_chatter_idx index. Bots are
excluded on the companion side (c.is_bot IS NOT TRUE, per creator_overlap's
convention); the anchor is a single caller-supplied id and is not re-checked here.
"""

from psycopg2.extensions import cursor as Cursor

from ...core.decorators import with_cursor
from .records import ChatCompanionRow


@with_cursor
def select_chat_companions_db(
    cursor: Cursor,
    chatter_id: int,
    limit: int = 8,
) -> list[ChatCompanionRow]:
    """Top co-chatters ranked by shared-stream count, bot companions excluded.

    :param chatter_id: The chatter whose companions are being looked up.
    :param limit: Maximum number of companions to return (default 8).
    :return: ChatCompanionRow records ordered by shared_streams DESC, then nick ASC.
    """
    cursor.execute(
        """
        SELECT co.chatter_id, c.nick, count(*) AS shared_streams
        FROM stream_chatter_stats a
        JOIN stream_chatter_stats co
            ON co.stream_id = a.stream_id AND co.chatter_id != a.chatter_id
        JOIN chatter c ON c.id = co.chatter_id
        WHERE a.chatter_id = %s
          AND c.is_bot IS NOT TRUE
        GROUP BY co.chatter_id, c.nick
        ORDER BY shared_streams DESC, c.nick ASC
        LIMIT %s
        """,
        (chatter_id, limit),
    )
    return [ChatCompanionRow(*row) for row in cursor.fetchall()]
