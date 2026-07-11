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
