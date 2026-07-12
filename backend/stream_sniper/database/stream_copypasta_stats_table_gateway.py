"""Database gateway for the per-stream copypasta rollup (stream_copypasta_stats).

Copypasta identity is the whole deduplicated message text (keyed on message_text_id),
NOT a tokenized n-gram. The rollup engine fills this table per-stream (index-supported
by the stream_id filter, applying junk + bot filters); the /scene/copypastas endpoint
aggregates the SMALL rollup table scene-wide — the raw `message` table is never scanned
on demand.
"""

from typing import List, Optional, Tuple

from psycopg2.extras import execute_values

from .decorators import with_cursor, with_cursor_connection

# Whitelisted sort: the caller-supplied `sort` maps through this dict to a fixed ORDER BY
# fragment, so no user string is ever interpolated into the query.
_COPYPASTA_SORT = {
    "usage": "usage_count DESC, message_text_id ASC",
    "spread": "creator_count DESC, usage_count DESC, message_text_id ASC",
    "recent": "last_stream_start DESC, message_text_id ASC",
}


@with_cursor
def select_stream_copypasta_source_db(stream_id, cursor):
    """Per-stream copypasta candidates: repeated, substantial, non-command messages from humans.

    Returns (message_text_id, usage_count, chatter_count, first_seen) rows. Bots are excluded
    (ch.is_bot IS NOT TRUE), commands (text starting '!') and short texts (< 20 chars) are
    dropped, and a row only qualifies when it was sent by >= 2 distinct chatters OR >= 3 times.
    """
    cursor.execute(
        """
        SELECT m.message_text_id, COUNT(*), COUNT(DISTINCT m.chatter_id), MIN(m.time)
        FROM message m
        JOIN message_text mt ON mt.id = m.message_text_id
        JOIN chatter ch ON ch.id = m.chatter_id
        WHERE m.stream_id = %s AND m.chatter_id IS NOT NULL
          AND ch.is_bot IS NOT TRUE
          AND char_length(mt.text) >= 20
          AND mt.text NOT LIKE '!%%'
        GROUP BY m.message_text_id
        HAVING COUNT(DISTINCT m.chatter_id) >= 2 OR COUNT(*) >= 3
        """,
        (stream_id,),
    )
    return cursor.fetchall()


@with_cursor_connection
def replace_stream_copypasta_stats_db(
    stream_id,
    rows: List[Tuple],
    cursor,
    connection,
):
    """Atomically replace this stream's copypasta rollup (DELETE per stream + execute_values INSERT).

    rows: (message_text_id, usage_count, chatter_count, first_seen) — the shape returned by
    select_stream_copypasta_source_db (first_seen is MIN(m.time), a datetime or None).
    """
    cursor.execute("DELETE FROM stream_copypasta_stats WHERE stream_id = %s", (stream_id,))
    if rows:
        execute_values(
            cursor,
            """
            INSERT INTO stream_copypasta_stats
                (stream_id, message_text_id, usage_count, chatter_count, first_seen)
            VALUES %s
            """,
            [
                (stream_id, message_text_id, usage_count, chatter_count, first_seen)
                for message_text_id, usage_count, chatter_count, first_seen in rows
            ],
        )
    connection.commit()


@with_cursor
def select_scene_copypastas_db(
    days: Optional[int],
    creator_id: Optional[int],
    sort: str,
    limit: int,
    offset: int,
    cursor,
):
    """Scene-wide copypasta aggregate over the small rollup table.

    Returns (rows, total) where rows are:
      (message_text_id, text, usage_count, chatter_appearances, stream_count, creator_count,
       first_seen_iso, last_stream_start_iso)
    Optional `days` window and `creator_id` filter narrow the aggregate; `sort` is whitelisted.
    chatter_appearances SUMs per-stream chatter_count, so it double-counts across streams
    (cross-stream distinct chatters is not reconstructable from per-stream counts).
    """
    order_by = _COPYPASTA_SORT.get(sort, _COPYPASTA_SORT["usage"])

    where_clauses = []
    params: list = []
    if days is not None:
        where_clauses.append("s.start >= (now() AT TIME ZONE 'UTC') - (%s * interval '1 day')")
        params.append(days)
    if creator_id is not None:
        where_clauses.append("s.creator_id = %s")
        params.append(creator_id)
    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    # Total distinct copypastas matching the filter (COUNT over the grouped subquery).
    cursor.execute(
        f"""
        SELECT COUNT(*) FROM (
            SELECT scs.message_text_id
            FROM stream_copypasta_stats scs
            JOIN stream s ON s.id = scs.stream_id
            {where_sql}
            GROUP BY scs.message_text_id
        ) grouped
        """,
        tuple(params),
    )
    total = cursor.fetchone()[0]

    cursor.execute(
        f"""
        SELECT scs.message_text_id, mt.text,
               SUM(scs.usage_count) AS usage_count,
               SUM(scs.chatter_count) AS chatter_appearances,
               COUNT(DISTINCT scs.stream_id) AS stream_count,
               COUNT(DISTINCT s.creator_id) AS creator_count,
               TO_CHAR(MIN(scs.first_seen), 'YYYY-MM-DD"T"HH24:MI:SS') AS first_seen,
               TO_CHAR(MAX(s.start), 'YYYY-MM-DD"T"HH24:MI:SS') AS last_stream_start
        FROM stream_copypasta_stats scs
        JOIN stream s ON s.id = scs.stream_id
        JOIN message_text mt ON mt.id = scs.message_text_id
        {where_sql}
        GROUP BY scs.message_text_id, mt.text
        ORDER BY {order_by}
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (limit, offset),
    )
    rows = cursor.fetchall()
    return rows, total
