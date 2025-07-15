from typing import List

from psycopg2.extras import execute_values

from .decorators import with_cursor_connection, with_cursor


@with_cursor_connection
def find_or_insert_message_text_id_db(message_text, cursor, connection):
    sql = """
    WITH e AS 
    (
        INSERT INTO 
        message_text 
            (text) 
        VALUES 
            (%s)
        ON CONFLICT DO NOTHING
        RETURNING id
    )
    SELECT * FROM e
    UNION
        SELECT id FROM message_text WHERE text = %s
    """
    cursor.execute(sql, (message_text, message_text))
    connection.commit()
    result = cursor.fetchone()[0]

    return result


@with_cursor_connection
def insert_message_texts_db(message_texts: List[str], cursor, connection):
    """

    :param message_texts: Texts of the messages
    :return: Created message texts IDs or Existing message texts IDs
    """
    sql = """
    INSERT INTO
        message_text
    (text)
        VALUES %s
    ON CONFLICT DO NOTHING
    """
    execute_values(cursor, sql, [(text,) for text in message_texts])

    connection.commit()


@with_cursor
def select_all_message_texts_db(cursor) -> dict:
    cursor.execute("SELECT id, text FROM message_text")
    return {x[1]: x[0] for x in cursor.fetchall()}
