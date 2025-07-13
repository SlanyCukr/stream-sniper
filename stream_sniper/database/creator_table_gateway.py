from .decorators import with_cursor, with_cursor_connection


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
def insert_new_creator_db(nick, display_name, profile_image_url, twitch_creator_id, cursor, connection):
    sql = """
    WITH e AS 
    (
        INSERT INTO
        creator 
            (nick, display_name, profile_image_url, twitch_id) 
        VALUES 
            (%s, %s, %s, %s) 
        ON CONFLICT DO NOTHING 
        RETURNING id
    )
    SELECT * FROM e
    UNION
        SELECT id FROM creator WHERE nick = %s
    """
    cursor.execute(sql, (nick, display_name, profile_image_url, twitch_creator_id, nick))
    connection.commit()

    return cursor.fetchone()[0]


@with_cursor
def select_creators_db(cursor):
    cursor.execute("SELECT id, display_name FROM creator")
    return cursor.fetchall()
