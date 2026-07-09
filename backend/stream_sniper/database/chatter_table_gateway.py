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
    :param prefix: The nick prefix the user has typed
    :param limit: Maximum number of suggestions to return
    :return: List of (id, nick) tuples ordered by nick
    """
    sql = """
    SELECT
        id,
        nick
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
