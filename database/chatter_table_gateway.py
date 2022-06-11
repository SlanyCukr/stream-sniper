from database.decorators import with_cursor, with_cursor_connection


@with_cursor
def select_all_chatters_on_stream_db(stream_id, cursor):
    cursor.execute("SELECT id, nick "
                   "FROM "
                   "chatter "
                   "WHERE id IN "
                   "(SELECT chatter_id FROM message WHERE stream_id = %s)", (stream_id,))
    return cursor.fetchall()


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