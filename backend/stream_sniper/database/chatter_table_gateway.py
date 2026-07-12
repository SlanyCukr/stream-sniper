from typing import List

from psycopg2.extras import execute_values

from .decorators import with_cursor, with_cursor_connection


@with_cursor
def select_all_chatters_on_stream_db(stream_id: int, cursor):
    sql = """
    SELECT
        id,
        nick
    FROM
        chatter
    WHERE id IN
        (SELECT chatter_id FROM message WHERE stream_id = %s)
    """

    cursor.execute(sql, (stream_id,))
    return cursor.fetchall()


@with_cursor_connection
def insert_new_chatter_db(nick, cursor, connection):
    """
    Tries to insert new chatter. If it can, then it returns his ID.
    If this function cannot insert, it returns existing chatters ID.
    :param nick: Nick of the chatter
    :return: Created chatters ID or Existing chatters ID
    """
    sql = """
    WITH e AS 
    (
        INSERT INTO 
        chatter 
            (nick) 
        VALUES 
            (%s) 
        ON CONFLICT DO NOTHING
        RETURNING id
    )
    SELECT * FROM e
    UNION
        SELECT id FROM chatter WHERE nick = %s
    """
    cursor.execute(sql, (nick, nick))
    connection.commit()

    return cursor.fetchone()[0]


@with_cursor_connection
def insert_new_chatters_db(nicks: List[str], cursor, connection) -> None:
    """
    Insert new chatters, skipping any that already exist (ON CONFLICT DO NOTHING).
    Callers fetch the resulting IDs separately via select_all_chatters_db().
    :param nicks: Nicks of the chatters
    """
    sql = """
    INSERT INTO 
    chatter 
        (nick) 
    VALUES 
        %s 
    ON CONFLICT DO NOTHING
    """
    execute_values(cursor, sql, [(nick,) for nick in nicks])
    connection.commit()


@with_cursor
def select_chatters_by_prefix_db(prefix: str, limit: int, cursor):
    """
    Case-insensitive prefix search over chatter nicks for autocomplete.
    Relies on the functional index chatter_nick_lower_prefix_idx
    (lower(nick) text_pattern_ops) so the LIKE prefix scan stays fast.
    Bots are NOT hidden here — is_bot rides along so the UI can badge them
    (NULL = not yet classified).
    :param prefix: The nick prefix the user has typed
    :param limit: Maximum number of suggestions to return
    :return: List of (id, nick, is_bot) tuples ordered by nick
    """
    sql = """
    SELECT
        id,
        nick,
        is_bot
    FROM
        chatter
    WHERE lower(nick) LIKE lower(%s) || '%%'
    ORDER BY lower(nick)
    LIMIT %s
    """
    cursor.execute(sql, (prefix, limit))
    return cursor.fetchall()


@with_cursor
def select_all_chatters_db(cursor) -> dict:
    sql = """
    SELECT
        id,
        nick
    FROM
        chatter
    """
    cursor.execute(sql)

    return {row[1]: row[0] for row in cursor.fetchall()}


@with_cursor_connection
def mark_bots_by_nick_db(nicks: List[str], reason: str, cursor, connection) -> int:
    """Mark chatters whose lowercased nick is in `nicks` as bots. Returns rows updated.

    Never un-marks or re-reasons an already-marked bot (is_bot IS NOT TRUE guard),
    so the first classification reason sticks.
    """
    if not nicks:
        return 0
    cursor.execute(
        """
        UPDATE chatter
        SET is_bot = TRUE, bot_reason = %s
        WHERE lower(nick) = ANY(%s) AND is_bot IS NOT TRUE
        """,
        (reason, [nick.lower() for nick in nicks]),
    )
    connection.commit()
    return cursor.rowcount


@with_cursor_connection
def mark_bots_by_ids_db(ids: List[int], reason: str, cursor, connection) -> int:
    """Mark the given chatter IDs as bots. Returns rows updated (already-marked are skipped)."""
    if not ids:
        return 0
    cursor.execute(
        """
        UPDATE chatter
        SET is_bot = TRUE, bot_reason = %s
        WHERE id = ANY(%s) AND is_bot IS NOT TRUE
        """,
        (reason, list(ids)),
    )
    connection.commit()
    return cursor.rowcount


@with_cursor
def select_bot_candidates_ubiquity_db(min_channels: int, cursor):
    """Unmarked chatters present in MORE THAN `min_channels` distinct creators' audiences.

    Reads the small creator_chatter_stats rollup (never the message table).
    :return: List of (chatter_id, channel_count) tuples, most ubiquitous first.
    """
    cursor.execute(
        """
        SELECT ccs.chatter_id, count(DISTINCT ccs.creator_id) AS channels
        FROM creator_chatter_stats ccs
        JOIN chatter c ON c.id = ccs.chatter_id
        WHERE c.is_bot IS NOT TRUE
        GROUP BY ccs.chatter_id
        HAVING count(DISTINCT ccs.creator_id) > %s
        ORDER BY channels DESC, ccs.chatter_id ASC
        """,
        (min_channels,),
    )
    return cursor.fetchall()


@with_cursor
def select_bot_candidates_rate_db(cursor, *, min_messages=200, min_rate=12.0, min_streams=3):
    """Unmarked chatters with a superhuman sustained message rate.

    A qualifying stream has message_count >= min_messages AND a sustained rate of
    message_count / active-minutes >= min_rate; a chatter qualifies with at least
    min_streams such streams. One SQL over the stream_chatter_stats rollup — no
    message scan.
    :return: List of (chatter_id, stream_count) tuples.
    """
    cursor.execute(
        """
        SELECT scs.chatter_id, count(*) AS streams
        FROM stream_chatter_stats scs
        JOIN chatter c ON c.id = scs.chatter_id
        WHERE c.is_bot IS NOT TRUE
          AND scs.message_count >= %s
          AND scs.message_count / NULLIF(
                EXTRACT(EPOCH FROM (scs.last_message_time - scs.first_message_time)) / 60.0, 0
              ) >= %s
        GROUP BY scs.chatter_id
        HAVING count(*) >= %s
        ORDER BY streams DESC, scs.chatter_id ASC
        """,
        (min_messages, min_rate, min_streams),
    )
    return cursor.fetchall()


@with_cursor
def count_bots_db(cursor) -> int:
    """Total chatters currently marked as bots."""
    cursor.execute("SELECT count(*) FROM chatter WHERE is_bot IS TRUE")
    return cursor.fetchone()[0]
