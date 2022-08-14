from database.decorators import with_cursor_connection


@with_cursor_connection
def find_or_insert_message_text_id_db(message_text, cursor, connection):
    cursor.execute("SELECT id FROM message_text WHERE text = %s LIMIT 1", (message_text,))
    result = cursor.fetchone()

    if not result:
        cursor.execute("INSERT INTO message_text (text) VALUES (%s)", (message_text,))
        connection.commit()
        if cursor.rowcount != 0:
            cursor.execute("SELECT LAST_INSERT_ID()")
            return cursor.fetchone()[0]

    return result[0]

