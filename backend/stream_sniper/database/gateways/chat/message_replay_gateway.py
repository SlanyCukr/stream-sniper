from typing import Any

from psycopg2.extensions import cursor as Cursor

from ...core.decorators import with_cursor
from .records import MessageReplayRow


@with_cursor
def select_stream_messages_db(
    cursor: Cursor,
    stream_id: int,
    limit: int,
    *,
    after_ts: str | None = None,
    after_id: int | None = None,
    chatter_id: int | None = None,
    q: str | None = None,
    sub_only: bool = False,
) -> list[MessageReplayRow]:
    conditions = ["m.stream_id = %s"]
    params: list[Any] = [stream_id]

    if after_ts is not None and after_id is not None:
        conditions.append("(m.time, m.id) > (%s::timestamp, %s)")
        params.append(after_ts)
        params.append(after_id)

    if chatter_id is not None:
        conditions.append("m.chatter_id = %s")
        params.append(chatter_id)

    if q is not None:
        conditions.append("mt.text ILIKE %s")
        params.append(f"%{q}%")

    if sub_only:
        conditions.append("m.is_subscriber IS TRUE")

    query = (
        "SELECT m.id, TO_CHAR(m.time, 'YYYY-MM-DD\"T\"HH24:MI:SS.US'), m.chatter_id, c.nick, mt.text, "
        "m.is_subscriber, m.badges\n"
        "FROM message m\n"
        "JOIN chatter c ON c.id = m.chatter_id\n"
        "JOIN message_text mt ON mt.id = m.message_text_id\n"
        f"WHERE {' AND '.join(conditions)}\n"
        "ORDER BY m.time ASC, m.id ASC\n"
        "LIMIT %s"
    )
    params.append(limit)

    cursor.execute(query, tuple(params))
    return [MessageReplayRow(*row) for row in cursor.fetchall()]
