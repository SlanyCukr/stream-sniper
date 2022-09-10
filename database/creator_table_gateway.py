from database.decorators import with_cursor, with_cursor_connection


@with_cursor
def select_creator_twitch_id_db(nick, cursor):
    cursor.execute("SELECT twitch_id FROM creator WHERE nick = %s", (nick,))
    return cursor.fetchone()[0]


@with_cursor
def select_creator_id_db(nick, cursor):
    cursor.execute("SELECT id FROM creator WHERE nick = %s", (nick,))
    result = cursor.fetchone()
    if result:
        return result[0]
    return None


@with_cursor_connection
def insert_new_creator_db(nick, display_name, profile_image_url, cursor, connection):
    cursor.execute("INSERT INTO creator "
                   "(nick, display_name, profile_image_url) "
                   "VALUES "
                   "(%s, %s, %s)", (nick, display_name, profile_image_url))
    connection.commit()

    if cursor.rowcount != 0:
        cursor.execute("SELECT LAST_INSERT_ID()")
        return cursor.fetchone()[0]
    return None


@with_cursor
def select_creators_db(cursor):
    cursor.execute("SELECT id, display_name FROM creator")
    return cursor.fetchall()
