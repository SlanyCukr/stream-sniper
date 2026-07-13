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


@with_cursor
def select_creator_summary_db(creator_id, cursor):
    """Return a cheap, dossier-ready creator summary from rollup tables only.

    The query deliberately never touches ``message``. Stream totals come from the
    one-row-per-stream metrics table and audience totals from the one-row-per
    creator/chatter table, so the endpoint remains suitable for the Pi deployment.
    """
    cursor.execute(
        """
        WITH stream_summary AS (
            SELECT
                COUNT(s.id)::int AS total_streams,
                MIN(s.start) AS first_stream_at,
                MAX(s.start) AS last_stream_at,
                COALESCE(SUM(s.message_count), 0)::bigint AS total_messages,
                SUM(sm.duration_seconds)::bigint AS duration_seconds,
                SUM(COALESCE(sm.total_messages, 0))::float
                    / NULLIF(SUM(COALESCE(sm.duration_seconds, 0)) / 60.0, 0)
                    AS messages_per_minute
            FROM stream s
            LEFT JOIN stream_metrics sm ON sm.stream_id = s.id
            WHERE s.creator_id = %(creator_id)s
        ),
        audience_summary AS (
            SELECT
                COUNT(*) FILTER (WHERE ch.is_bot IS NOT TRUE)::int AS audience_size,
                COUNT(*) FILTER (
                    WHERE ch.is_bot IS NOT TRUE AND ccs.streams_attended >= 3
                )::int AS regulars
            FROM creator_chatter_stats ccs
            JOIN chatter ch ON ch.id = ccs.chatter_id
            WHERE ccs.creator_id = %(creator_id)s
        ),
        latest_stream AS (
            SELECT s.id, s.title, s.start
            FROM stream s
            WHERE s.creator_id = %(creator_id)s
            ORDER BY s.start DESC NULLS LAST, s.id DESC
            LIMIT 1
        )
        SELECT
            c.id, c.nick, c.display_name, c.profile_image_url, c.twitch_id,
            ss.total_streams,
            TO_CHAR(ss.first_stream_at, 'YYYY-MM-DD"T"HH24:MI:SS'),
            TO_CHAR(ss.last_stream_at, 'YYYY-MM-DD"T"HH24:MI:SS'),
            ss.total_messages, ss.duration_seconds, ss.messages_per_minute,
            COALESCE(a.audience_size, 0), COALESCE(a.regulars, 0),
            ls.id, ls.title, TO_CHAR(ls.start, 'YYYY-MM-DD"T"HH24:MI:SS')
        FROM creator c
        CROSS JOIN stream_summary ss
        CROSS JOIN audience_summary a
        LEFT JOIN latest_stream ls ON TRUE
        WHERE c.id = %(creator_id)s
        """,
        {"creator_id": creator_id},
    )
    return cursor.fetchone()


@with_cursor
def select_creator_top_chatters_db(creator_id, limit, cursor):
    cursor.execute(
        """
    SELECT m.chatter_id, c.nick, COUNT(*) AS message_count
    FROM message m
    JOIN stream s ON s.id = m.stream_id
    JOIN chatter c ON c.id = m.chatter_id
    WHERE s.creator_id = %s
    GROUP BY m.chatter_id, c.nick
    ORDER BY message_count DESC
    LIMIT %s
    """,
        (creator_id, limit),
    )
    return cursor.fetchall()
