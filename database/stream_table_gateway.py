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
def select_all_streams_db(creator_id, offset, cursor):
    if creator_id == -1:
        cursor.execute("""
            SELECT stream.id, display_name, start, `end`, thumbnail_url, message_count 
            FROM stream 
            JOIN creator ON stream.creator_id = creator.id ORDER BY start DESC LIMIT 20 OFFSET %s""", (offset,))
    else:
        cursor.execute("""SELECT stream.id, display_name, start, `end`, thumbnail_url, message_count 
                               FROM stream
                               JOIN creator ON stream.creator_id = creator.id
                               WHERE stream.creator_id = %s ORDER BY start DESC LIMIT 20 OFFSET %s""", (creator_id, offset))
    return cursor.fetchall()


@with_cursor
def select_all_stream_count_db(creator_id, cursor):
    if creator_id == -1:
        cursor.execute("SELECT COUNT(*) FROM stream")
    else:
        cursor.execute("SELECT COUNT(*) FROM stream WHERE creator_id = %s", (creator_id,))
    return cursor.fetchone()[0]


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


@with_cursor_connection
def update_stream_message_count_db(stream_id, message_count, cursor, connection):
    cursor.execute("UPDATE stream SET message_count = %s WHERE id = %s", (message_count, stream_id))
    connection.commit()


@with_cursor
def select_stream_comprehensive_db(stream_id, cursor):
    cursor.execute("SELECT "
                   "title, `start`, `end`, thumbnail_url, message_count, nick, display_name, profile_image_url, creator_id "
                   "FROM stream "
                   "JOIN creator ON stream.creator_id = creator.id "
                   "AND stream.id = %s", (stream_id,))
    return cursor.fetchone()


@with_cursor
def select_most_active_chatters_db(stream_id, cursor):
    cursor.execute("""
    SELECT chatter_id, (SELECT nick FROM chatter WHERE chatter.id = message.chatter_id), COUNT(chatter_id) AS message_count
     FROM message 
     WHERE stream_id = %s 
     GROUP BY chatter_id 
     ORDER BY message_count DESC 
     LIMIT 3
    """, (stream_id,))
    return cursor.fetchall()


@with_cursor
def select_most_tagged_chatters_db(stream_id, cursor):
    cursor.execute("""
    SELECT tagged_chatter_id, (SELECT nick FROM chatter WHERE chatter.id = tagged_chatter_id), COUNT(tagged_chatter_id) AS tag_count
     FROM message 
     WHERE 
     stream_id = %s 
     GROUP BY tagged_chatter_id 
     HAVING tagged_chatter_id IS NOT NULL 
     ORDER BY tag_count DESC 
     LIMIT 3
    """, (stream_id,))
    return cursor.fetchall()


@with_cursor
def select_creators_that_wrote_in_stream_db(stream_id, creator_id, cursor):
    cursor.execute("""
    SELECT DISTINCT(chatter_id), (SELECT nick FROM chatter WHERE chatter_id = chatter.id) AS nick 
    FROM message 
    WHERE 
    chatter_id IN (SELECT chatter.id FROM chatter WHERE nick IN (SELECT nick FROM creator WHERE creator.id != %s))
    AND stream_id = %s
    """, (creator_id, stream_id))
    return cursor.fetchall()


@with_cursor
def select_chatters_in_stream_db(stream_id, cursor):
    cursor.execute("""
    SELECT DISTINCT(chatter_id), (SELECT nick FROM chatter WHERE chatter.id = chatter_id ) FROM message WHERE stream_id = %s
    """, (stream_id,))
    return cursor.fetchall()


@with_cursor
def select_chatter_messages_on_stream_db(stream_id, chatter_id, cursor):
    cursor.execute("""
    SELECT (SELECT text FROM message_text WHERE id = message.message_text_id) FROM message WHERE stream_id = %s AND chatter_id = %s
    """, (stream_id, chatter_id))
    return cursor.fetchall()