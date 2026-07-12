from .decorators import with_cursor


@with_cursor
def select_chatter_messages_db(chatter_id, limit, offset, cursor):
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
    return cursor.fetchall()


@with_cursor
def select_chatter_message_count_db(chatter_id, cursor):
    cursor.execute("SELECT COUNT(*) FROM message WHERE chatter_id = %s", (chatter_id,))
    return cursor.fetchone()[0]


def insert_message_db(items: list[tuple], cursor, connection):
    cursor.executemany(
        "INSERT INTO message "
        "(chatter_id, tagged_chatter_id, stream_id, message_text_id, time, "
        " is_subscriber, badges, emote_count) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        items,
    )
    connection.commit()


@with_cursor
def select_stream_phrase_source_db(stream_id, cursor):
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
    return cursor.fetchall()


@with_cursor
def select_moment_window_messages_db(stream_id, windows, cursor):
    """Fetch every message inside ANY moment window in a single query (no per-moment N+1).

    ``windows`` is a list of (start_datetime, end_datetime) half-open ranges. Returns
    (time, text, chatter_id, is_subscriber, emote_count); the caller partitions rows into windows
    in memory. Returns [] when there are no windows.
    """
    if not windows:
        return []
    clauses = []
    params: list = [stream_id]
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
    return cursor.fetchall()


@with_cursor
def select_chatter_id_db(nick, cursor):
    """Return (id, is_bot) for a nick, or None. is_bot is trailing: NULL = not yet classified."""
    cursor.execute("SELECT id, is_bot FROM chatter WHERE nick = %s", (nick,))
    return cursor.fetchone()


@with_cursor
def select_chatter_stream_activity_db(chatter_id, cursor):
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
    return cursor.fetchall()
