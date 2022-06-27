from database.decorators import with_cursor


@with_cursor
def select_chatter_messages_db(chatter_id, cursor):
    cursor.execute("SELECT message, time FROM message WHERE chatter_id = %s", (chatter_id,))
    return cursor.fetchall()


def insert_message_db(items: [tuple], cursor, connection):
    cursor.executemany("INSERT INTO "
               "message "
               "(chatter_id, tagged_chatter_id, stream_id, message, `time`) "
               "VALUES "
               "(%s, %s, %s, %s, %s)", items)
    connection.commit()


@with_cursor
def select_chatter_id_db(nick, cursor):
    cursor.execute("SELECT id FROM chatter WHERE nick = %s", (nick,))
    return cursor.fetchone()