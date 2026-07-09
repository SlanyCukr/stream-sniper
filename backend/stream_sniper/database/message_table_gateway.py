from .decorators import with_cursor


@with_cursor
def select_chatter_messages_db(chatter_id, cursor):
    # NOTE: the message table has no "message" column — selecting one used to
    # silently resolve to the whole-row composite. Join message_text for the
    # actual text and format time as a string for the JSON response model.
    cursor.execute(
        """
        SELECT (SELECT text FROM message_text WHERE id = message.message_text_id),
               TO_CHAR(time, 'YYYY-MM-DD HH24:MI:SS')
        FROM message WHERE chatter_id = %s ORDER BY time
        """,
        (chatter_id,),
    )
    return cursor.fetchall()


def insert_message_db(items: list[tuple], cursor, connection):
    cursor.executemany(
        "INSERT INTO "
        "message "
        "(chatter_id, tagged_chatter_id, stream_id, message_text_id, time) "
        "VALUES "
        "(%s, %s, %s, %s, %s)",
        items,
    )
    connection.commit()


@with_cursor
def select_chatter_id_db(nick, cursor):
    cursor.execute("SELECT id FROM chatter WHERE nick = %s", (nick,))
    return cursor.fetchone()


@with_cursor
def select_chatter_stream_activity_db(chatter_id, cursor):
    cursor.execute(
        """
    SELECT m.stream_id, s.title, s.start, cr.id, cr.display_name, COUNT(*) AS message_count
    FROM message m
    JOIN stream s ON s.id = m.stream_id
    JOIN creator cr ON cr.id = s.creator_id
    WHERE m.chatter_id = %s
    GROUP BY m.stream_id, s.title, s.start, cr.id, cr.display_name
    ORDER BY message_count DESC
    LIMIT 100
    """,
        (chatter_id,),
    )
    return cursor.fetchall()
