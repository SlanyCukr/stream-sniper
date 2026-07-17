from collections.abc import Sequence

from psycopg2.extensions import connection as Connection
from psycopg2.extensions import cursor as Cursor
from psycopg2.extras import execute_values

from stream_sniper.database.gateways.streams.records import StreamParticipantRow

from ...core.decorators import with_cursor, with_cursor_connection
from .records import ChatterSearchRow


@with_cursor
def select_all_chatters_on_stream_db(
    cursor: Cursor,
    stream_id: int,
) -> list[StreamParticipantRow]:
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
    return [StreamParticipantRow(*row) for row in cursor.fetchall()]


@with_cursor_connection
def find_or_insert_chatter_id_db(
    cursor: Cursor,
    connection: Connection,
    nick: str,
) -> int:
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

    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("chatter upsert returned no id")
    return int(row[0])


@with_cursor_connection
def insert_new_chatters_db(
    cursor: Cursor,
    connection: Connection,
    nicks: Sequence[str],
) -> None:
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
def select_chatters_by_prefix_db(
    cursor: Cursor,
    prefix: str,
    limit: int,
) -> list[ChatterSearchRow]:
    """
    Case-insensitive prefix search over chatter nicks for autocomplete.
    Relies on the functional index chatter_nick_lower_prefix_idx
    (lower(nick) text_pattern_ops) so the LIKE prefix scan stays fast.
    Bots are NOT hidden here — is_bot rides along so the UI can badge them
    (NULL = not yet classified).
    :param prefix: The nick prefix the user has typed
    :param limit: Maximum number of suggestions to return
    :return: ChatterSearchRow records ordered by nick
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
    return [ChatterSearchRow(*row) for row in cursor.fetchall()]


@with_cursor
def select_all_chatters_db(
    cursor: Cursor,
) -> dict[str, int]:
    sql = """
    SELECT
        id,
        nick
    FROM
        chatter
    """
    cursor.execute(sql)

    return {str(row[1]): int(row[0]) for row in cursor.fetchall()}


@with_cursor
def select_unmarked_known_bots_db(
    cursor: Cursor,
    nicks: Sequence[str],
) -> list[tuple[int, str]]:
    """Chatters whose lowercased nick is in `nicks` and who are not yet marked as bots.

    Feeds the known-name classification pass: the caller marks the returned ids (so it
    knows exactly which chatters were newly flagged) and dry-run reports the real
    candidate count instead of the size of the curated list.
    :return: List of (chatter_id, nick) tuples ordered by nick.
    """
    if not nicks:
        return []
    cursor.execute(
        """
        SELECT id, nick
        FROM chatter
        WHERE lower(nick) = ANY(%s) AND is_bot IS NOT TRUE
        ORDER BY nick ASC
        """,
        ([nick.lower() for nick in nicks],),
    )
    return cursor.fetchall()


@with_cursor_connection
def mark_bots_by_ids_db(
    cursor: Cursor,
    connection: Connection,
    ids: Sequence[int],
    reason: str,
) -> int:
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
    return int(cursor.rowcount)


@with_cursor
def select_bot_candidates_ubiquity_db(
    cursor: Cursor,
    min_channels: int,
) -> list[tuple[int, int]]:
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
def select_bot_candidates_rate_db(
    cursor: Cursor,
    *,
    min_messages: int = 200,
    min_rate: float = 12.0,
    min_streams: int = 3,
) -> list[tuple[int, int]]:
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
def count_bots_db(
    cursor: Cursor,
) -> int:
    """Total chatters currently marked as bots."""
    cursor.execute("SELECT count(*) FROM chatter WHERE is_bot IS TRUE")
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("bot count returned no row")
    return int(row[0])
