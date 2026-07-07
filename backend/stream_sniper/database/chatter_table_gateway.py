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
def insert_new_chatters_db(nicks: List[str], cursor, connection) -> List[int]:
    """
    Tries to insert new chatters. If it can, then it returns their IDs.
    If this function cannot insert, it returns existing chatters IDs.
    :param nicks: Nicks of the chatters
    :return: Created chatters IDs or Existing chatters IDs
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
