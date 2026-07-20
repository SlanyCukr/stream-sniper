from collections.abc import Sequence

from psycopg2.extensions import connection as Connection
from psycopg2.extensions import cursor as Cursor
from psycopg2.extras import execute_values

from ...core.decorators import with_cursor, with_cursor_connection


@with_cursor_connection
def find_or_insert_message_text_id_db(
    cursor: Cursor,
    connection: Connection,
    message_text: str,
) -> int:
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
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("message text upsert returned no id")
    result = int(row[0])

    return result


@with_cursor_connection
def insert_message_texts_db(
    cursor: Cursor,
    connection: Connection,
    message_texts: Sequence[str],
) -> None:
    """

    :param message_texts: Texts of the messages
    Bulk-insert missing message texts; callers can select identifiers separately.
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
def select_message_text_ids_db(
    cursor: Cursor,
    texts: Sequence[str],
) -> dict[str, int]:
    """Text -> id map for exactly the given texts (batch-scoped dedup lookup).

    Replaces a former full-table scan: the dedup table grows with all history,
    so lookups must stay bounded by the ingestion batch, not table size.
    """
    if not texts:
        return {}
    cursor.execute("SELECT id, text FROM message_text WHERE text = ANY(%s)", (list(texts),))
    return {str(row[1]): int(row[0]) for row in cursor.fetchall()}
