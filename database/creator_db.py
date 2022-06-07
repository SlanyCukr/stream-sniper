from database.decorators import with_cursor, with_cursor_connection


@with_cursor
def select_creator_twitch_id_db(nick, cursor):
    cursor.execute("SELECT twitch_id FROM creator WHERE nick = %s", (nick,))
    return cursor.fetchone()[0]