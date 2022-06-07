from database.decorators import with_cursor, with_cursor_connection


@with_cursor
def select_creator_id_db(nick, cursor):
    cursor.execute("SELECT id FROM creator WHERE nick = %s", (nick,))
    result = cursor.fetchone()
    if result:
        return result[0]
    return None


@with_cursor_connection
def insert_new_creator_db(nick, cursor, connection):
    cursor.execute("INSERT INTO creator (nick) VALUES (%s)", (nick,))
    connection.commit()

    if cursor.rowcount != 0:
        cursor.execute("SELECT LAST_INSERT_ID()")
        return cursor.fetchone()[0]
    return None


@with_cursor_connection
def insert_new_chatter_db(nick, cursor, connection):
    """
    Tries to insert new chatter. If it can, then it returns his ID.
    If this function cannot insert, it returns existing chatters ID.
    :param nick: Nick of the chatter
    :return: Created chatters ID or Existing chatters ID
    """
    try:
        cursor.execute("INSERT INTO chatter (nick) VALUES (%s)", (nick,))
        connection.commit()
        cursor.execute("SELECT LAST_INSERT_ID()")
        return cursor.fetchone()[0]
    except:
        cursor.execute("SELECT id FROM chatter WHERE nick = %s", (nick,))
        return cursor.fetchone()[0]


@with_cursor_connection
def insert_message_db(chatter_id, tagged_chatter_id, stream_id, message, message_timestamp, cursor, connection):
    cursor.execute("INSERT INTO "
               "message "
               "(chatter_id, tagged_chatter_id, stream_id, message, `time`) "
               "VALUES "
               "(%s, %s, %s, %s, %s)", (chatter_id, tagged_chatter_id, stream_id, message, message_timestamp))
    connection.commit()


@with_cursor_connection
def insert_stream_db(stream_id, start, creator_id, cursor, connection):
    try:
        cursor.execute("INSERT INTO stream (twitch_id, `start`, creator_id) VALUES (%s, %s, %s)", (stream_id, start, creator_id))
        connection.commit()
        cursor.execute("SELECT LAST_INSERT_ID()")
        return cursor.fetchone()[0]
    except:
        # stream is already in database, but that's ok, return its id
        cursor.execute("SELECT `id` FROM stream WHERE twitch_id = %s", (stream_id,))
        return cursor.fetchone()[0]
