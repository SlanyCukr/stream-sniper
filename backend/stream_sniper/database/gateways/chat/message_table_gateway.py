from collections.abc import Sequence
from datetime import datetime

from psycopg2.extensions import connection as Connection
from psycopg2.extensions import cursor as Cursor

from ...core.decorators import with_cursor
from .records import (
    ChatterIdentityRow,
    ChatterMessageRow,
    ChatterStreamActivityRow,
    MomentWindowRow,
    PhraseSourceRow,
)


@with_cursor
def select_chatter_messages_db(
    cursor: Cursor,
    chatter_id: int,
    limit: int,
    offset: int,
) -> list[ChatterMessageRow]:
    cursor.execute(
        """
        SELECT m.stream_id, s.title, cr.display_name, mt.text,
               TO_CHAR(m.time, 'YYYY-MM-DD HH24:MI:SS')
        FROM message m
        JOIN stream s ON s.id = m.stream_id
        JOIN creator cr ON cr.id = s.creator_id
        JOIN message_text mt ON mt.id = m.message_text_id
        WHERE m.chatter_id = %s
        ORDER BY m.time DESC
        LIMIT %s OFFSET %s
        """,
        (chatter_id, limit, offset),
    )
    return [ChatterMessageRow(*row) for row in cursor.fetchall()]


@with_cursor
def select_chatter_message_count_db(
    cursor: Cursor,
    chatter_id: int,
) -> int:
    cursor.execute("SELECT COUNT(*) FROM message WHERE chatter_id = %s", (chatter_id,))
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("chatter message count returned no row")
    return int(row[0])


def insert_message_db(items: Sequence[tuple[object, ...]], cursor: Cursor, connection: Connection) -> None:
    cursor.executemany(
        "INSERT INTO message "
        "(chatter_id, tagged_chatter_id, stream_id, message_text_id, time, "
        " is_subscriber, badges, emote_count, source_message_id) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s) "
        "ON CONFLICT (source_message_id) WHERE source_message_id IS NOT NULL DO NOTHING",
        items,
    )
    connection.commit()


@with_cursor
def select_stream_phrase_source_db(
    cursor: Cursor,
    stream_id: int,
) -> list[PhraseSourceRow]:
    """Per (text, chatter) occurrence counts for a stream, feeding the Python phrase rollup.

    Returns (text, chatter_id, occurrence_count). Grouping on (text, chatter_id) lets the phrase
    stats dedupe chatter_count on (phrase, chatter_id) while still summing repeated sends.
    """
    cursor.execute(
        """
        SELECT mt.text, m.chatter_id, count(*)
        FROM message m
        JOIN message_text mt ON mt.id = m.message_text_id
        WHERE m.stream_id = %s AND m.chatter_id IS NOT NULL
        GROUP BY mt.text, m.chatter_id
        """,
        (stream_id,),
    )
    return [PhraseSourceRow(*row) for row in cursor.fetchall()]


@with_cursor
def select_moment_window_messages_db(
    cursor: Cursor,
    stream_id: int,
    windows: Sequence[tuple[datetime, datetime]],
) -> list[MomentWindowRow]:
    """Fetch every message inside ANY moment window in a single query (no per-moment N+1).

    ``windows`` is a list of (start_datetime, end_datetime) half-open ranges. Returns
    (time, text, chatter_id, is_subscriber, emote_count); the caller partitions rows into windows
    in memory. Returns [] when there are no windows.
    """
    if not windows:
        return []
    clauses = []
    params: list[object] = [stream_id]
    for start, end in windows:
        clauses.append("(m.time >= %s AND m.time < %s)")
        params.append(start)
        params.append(end)
    cursor.execute(
        f"""
        SELECT m.time, mt.text, m.chatter_id, m.is_subscriber, m.emote_count
        FROM message m
        JOIN message_text mt ON mt.id = m.message_text_id
        WHERE m.stream_id = %s AND ({" OR ".join(clauses)})
        """,
        tuple(params),
    )
    return [MomentWindowRow(*row) for row in cursor.fetchall()]


@with_cursor
def select_chatter_identity_db(
    cursor: Cursor,
    nick: str,
) -> ChatterIdentityRow | None:
    """Return (id, is_bot) for a nick, or None. is_bot is trailing: NULL = not yet classified."""
    cursor.execute("SELECT id, is_bot FROM chatter WHERE nick = %s", (nick,))
    row = cursor.fetchone()
    return ChatterIdentityRow(*row) if row is not None else None


@with_cursor
def select_chatter_stream_activity_db(
    cursor: Cursor,
    chatter_id: int,
) -> list[ChatterStreamActivityRow]:
    """Per-stream footprint rows for a chatter, with the chatter's is_bot flag trailing."""
    cursor.execute(
        """
    SELECT m.stream_id, s.title, s.start, cr.id, cr.display_name, COUNT(*) AS message_count,
           ch.is_bot
    FROM message m
    JOIN stream s ON s.id = m.stream_id
    JOIN creator cr ON cr.id = s.creator_id
    JOIN chatter ch ON ch.id = m.chatter_id
    WHERE m.chatter_id = %s
    GROUP BY m.stream_id, s.title, s.start, cr.id, cr.display_name, ch.is_bot
    ORDER BY message_count DESC
    LIMIT 100
    """,
        (chatter_id,),
    )
    return [ChatterStreamActivityRow(*row) for row in cursor.fetchall()]
