from .decorators import with_cursor, with_cursor_connection


@with_cursor
def select_last_twitch_stream_id_db(creator_nick, cursor):
    cursor.execute(
        "SELECT twitch_id FROM "
        "stream "
        "WHERE creator_id = "
        "(SELECT id FROM creator WHERE nick = %s) "
        "ORDER BY twitch_id DESC "
        "LIMIT 1",
        (creator_nick,),
    )
    result = cursor.fetchone()
    if not result:
        return None
    return result[0]


@with_cursor
def select_all_processed_stream_ids_db(creator_nick, cursor):
    cursor.execute(
        "SELECT twitch_id " "FROM " "stream " "WHERE " "creator_id = " "(SELECT id FROM creator WHERE nick = %s)",
        (creator_nick,),
    )
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
    # Base SQL query with TO_CHAR to return datetime as string
    base_query = """
    SELECT 
        stream.id,
        display_name, 
        TO_CHAR(start, 'YYYY-MM-DD HH24:MI:SS') AS start,
        TO_CHAR("end", 'YYYY-MM-DD HH24:MI:SS') AS "end", 
        thumbnail_url,
        message_count
    FROM stream
    JOIN creator ON stream.creator_id = creator.id
    """

    # Modify query based on whether creator_id is provided or not
    if creator_id == -1:
        query = base_query + " ORDER BY start DESC LIMIT 20 OFFSET %s"
        params = (offset,)
    else:
        query = base_query + " WHERE stream.creator_id = %s ORDER BY start DESC LIMIT 20 OFFSET %s"
        params = (creator_id, offset)

    # Execute the query with parameters
    cursor.execute(query, params)

    # Return the result
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
    sql = """
    WITH e AS 
    (
        INSERT INTO 
        stream 
            (twitch_id, start, creator_id, title, "end", thumbnail_url)
        VALUES
            (%s, %s, %s, %s, %s, %s)
        ON CONFLICT DO NOTHING
        RETURNING id
    )
    SELECT * FROM e
    UNION
        SELECT id FROM stream WHERE twitch_id = %s
    """
    cursor.execute(sql, (stream_id, start, creator_id, title, stopped_at, thumbnail_url, stream_id))
    connection.commit()

    return cursor.fetchone()[0]


@with_cursor_connection
def update_stream_message_count_db(stream_id, message_count, cursor, connection):
    cursor.execute("UPDATE stream SET message_count = %s WHERE id = %s", (message_count, stream_id))
    connection.commit()


@with_cursor
def select_stream_comprehensive_db(stream_id, cursor):
    sql = """
    SELECT
        title,
        start,
        "end",
        thumbnail_url,
        message_count,
        nick,
        display_name,
        profile_image_url,
        creator_id
    FROM stream
    JOIN creator ON stream.creator_id = creator.id AND stream.id = %s
    """
    cursor.execute(sql, (stream_id,))
    return cursor.fetchone()


@with_cursor
def select_most_active_chatters_db(stream_id, cursor):
    cursor.execute(
        """
    SELECT chatter_id, (SELECT nick FROM chatter WHERE chatter.id = message.chatter_id), COUNT(chatter_id) AS message_count
     FROM message 
     WHERE stream_id = %s 
     GROUP BY chatter_id 
     ORDER BY message_count DESC 
     LIMIT 3
    """,
        (stream_id,),
    )
    return cursor.fetchall()


@with_cursor
def select_most_tagged_chatters_db(stream_id, cursor):
    cursor.execute(
        """
    SELECT tagged_chatter_id, (SELECT nick FROM chatter WHERE chatter.id = tagged_chatter_id), COUNT(tagged_chatter_id) AS tag_count
     FROM message 
     WHERE 
     stream_id = %s 
     GROUP BY tagged_chatter_id 
     HAVING tagged_chatter_id IS NOT NULL 
     ORDER BY tag_count DESC 
     LIMIT 3
    """,
        (stream_id,),
    )
    return cursor.fetchall()


@with_cursor
def select_creators_that_wrote_in_stream_db(stream_id, creator_id, cursor):
    cursor.execute(
        """
    SELECT DISTINCT(chatter_id), (SELECT nick FROM chatter WHERE chatter_id = chatter.id) AS nick 
    FROM message 
    WHERE 
    chatter_id IN (SELECT chatter.id FROM chatter WHERE nick IN (SELECT nick FROM creator WHERE creator.id != %s))
    AND stream_id = %s
    """,
        (creator_id, stream_id),
    )
    return cursor.fetchall()


@with_cursor
def select_chatters_in_stream_db(stream_id, cursor):
    cursor.execute(
        """
    SELECT DISTINCT(chatter_id), (SELECT nick FROM chatter WHERE chatter.id = chatter_id ) FROM message WHERE stream_id = %s
    """,
        (stream_id,),
    )
    return cursor.fetchall()


@with_cursor
def select_chatter_messages_on_stream_db(stream_id, chatter_id, cursor):
    cursor.execute(
        """
    SELECT (SELECT text FROM message_text WHERE id = message.message_text_id) FROM message WHERE stream_id = %s AND chatter_id = %s
    """,
        (stream_id, chatter_id),
    )
    return cursor.fetchall()
