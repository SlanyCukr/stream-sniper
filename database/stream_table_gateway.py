from database.decorators import with_cursor, with_cursor_connection


@with_cursor
def select_last_twitch_stream_id_db(creator_nick, cursor):
    cursor.execute("SELECT twitch_id FROM "
                   "stream "
                   "WHERE creator_id = "
                   "(SELECT id FROM creator WHERE nick = %s) "
                   "ORDER BY twitch_id DESC "
                   "LIMIT 1", (creator_nick,))
    result = cursor.fetchone()
    if not result:
        return None
    return result[0]


@with_cursor
def select_all_processed_stream_ids_db(creator_nick, cursor):
    cursor.execute("SELECT twitch_id "
                   "FROM "
                   "stream "
                   "WHERE "
                   "creator_id = "
                   "(SELECT id FROM creator WHERE nick = %s)", (creator_nick,))
    result = cursor.fetchall()
    if not result:
        return []

    return [x[0] for x in result]


@with_cursor
def select_stream_by_twitch_id_db(twitch_id, cursor):
    cursor.execute("SELECT id FROM stream WHERE twitch_id = %s", (twitch_id,))
    return cursor.fetchone()


@with_cursor
def select_all_streams_db(cursor):
    cursor.execute("SELECT stream.id, start, display_name, thumbnail_url FROM stream JOIN creator ON stream.creator_id = creator.id")
    return cursor.fetchall()


@with_cursor_connection
def insert_stream_db(stream_id, start, creator_id, title, stopped_at, thumbnail_url, cursor, connection):
    try:
        cursor.execute("INSERT INTO "
                       "stream "
                       "(twitch_id, `start`, creator_id, title, `end`, thumbnail_url) "
                       "VALUES (%s, %s, %s, %s, %s, %s)", (stream_id, start, creator_id, title, stopped_at, thumbnail_url))
        connection.commit()
        cursor.execute("SELECT LAST_INSERT_ID()")
        return cursor.fetchone()[0]
    except:
        # stream is already in database, but that's ok, return its id
        cursor.execute("SELECT `id` FROM stream WHERE twitch_id = %s", (stream_id,))
        return cursor.fetchone()[0]
