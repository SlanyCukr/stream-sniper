from typing import Any, NamedTuple

from psycopg2.extensions import cursor as Cursor

from ...core.decorators import with_cursor
from .records import MessageReplayRow

# Shared replay projection (matches MessageReplayRow field order).
_REPLAY_COLUMNS = (
    "m.id, TO_CHAR(m.time, 'YYYY-MM-DD\"T\"HH24:MI:SS.US'), m.chatter_id, c.nick, mt.text, "
    "m.is_subscriber, m.badges"
)
_REPLAY_JOINS = "FROM message m\nJOIN chatter c ON c.id = m.chatter_id\nJOIN message_text mt ON mt.id = m.message_text_id"


class StreamContextRow(NamedTuple):
    """Minimal stream + creator header for the search-context view."""

    stream_id: int
    stream_title: str
    creator_id: int
    creator_nick: str
    creator_display_name: str


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


@with_cursor
def select_message_window_db(
    cursor: Cursor,
    stream_id: int,
    message_id: int,
    radius: int,
) -> list[MessageReplayRow]:
    """Replay-shaped window of ``radius`` messages on each side of a target message.

    The result includes the target itself and is ordered chronologically. Returns []
    when the message id does not belong to the stream (empty CTE -> empty branches),
    which the caller treats as "not found".
    """
    cursor.execute(
        "WITH target AS (\n"
        "    SELECT time AS t, id AS i FROM message WHERE id = %s AND stream_id = %s\n"
        ")\n"
        "SELECT * FROM (\n"
        f"    (SELECT {_REPLAY_COLUMNS}\n"
        f"     {_REPLAY_JOINS}, target\n"
        "     WHERE m.stream_id = %s AND (m.time, m.id) <= (target.t, target.i)\n"
        "     ORDER BY m.time DESC, m.id DESC\n"
        "     LIMIT %s)\n"
        "    UNION ALL\n"
        f"    (SELECT {_REPLAY_COLUMNS}\n"
        f"     {_REPLAY_JOINS}, target\n"
        "     WHERE m.stream_id = %s AND (m.time, m.id) > (target.t, target.i)\n"
        "     ORDER BY m.time ASC, m.id ASC\n"
        "     LIMIT %s)\n"
        ") w\n"
        # Columns 2 (ISO time) then 1 (id) reproduce the keyset chronological order.
        "ORDER BY 2 ASC, 1 ASC",
        (message_id, stream_id, stream_id, radius + 1, stream_id, radius),
    )
    return [MessageReplayRow(*row) for row in cursor.fetchall()]


@with_cursor
def select_stream_context_db(cursor: Cursor, stream_id: int) -> StreamContextRow | None:
    """Stream title + owning creator header, or None if the stream is unknown."""
    cursor.execute(
        "SELECT s.id, s.title, cr.id, cr.nick, cr.display_name\n"
        "FROM stream s\n"
        "JOIN creator cr ON cr.id = s.creator_id\n"
        "WHERE s.id = %s",
        (stream_id,),
    )
    row = cursor.fetchone()
    return StreamContextRow(*row) if row is not None else None
