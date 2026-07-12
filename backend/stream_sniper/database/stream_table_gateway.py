from .decorators import with_cursor, with_cursor_connection

# Hardcoded whitelists — user-supplied sort/dir values map through these fixed
# fragments so no request string is ever interpolated into SQL. FastAPI validates
# the values with Query(pattern=...) before they reach the gateway; the .get()
# fallbacks keep any direct caller safe as well.
_SORT_COLUMNS = {
    "start": "stream.start",
    "message_count": "stream.message_count",
    "duration": 'EXTRACT(EPOCH FROM (stream."end" - stream.start))',
}
_DIR = {"asc": "ASC", "desc": "DESC"}


def _build_stream_filter(creator_id, title, date_from, date_to, min_messages):
    """Build the shared WHERE clause + params for stream listing and its COUNT(*).

    Both select_all_streams_db and select_all_stream_count_db route through this so the
    filtered rows and the filtered count (which feeds max_offset) can never diverge.
    Returns (where_sql, params) where where_sql is "" or "WHERE ...".
    """
    conditions = []
    params = []

    if creator_id != -1:
        conditions.append("stream.creator_id = %s")
        params.append(creator_id)
    if title:
        conditions.append("stream.title ILIKE %s")
        params.append(f"%{title}%")
    if date_from is not None:
        conditions.append("stream.start >= %s")
        params.append(date_from)
    if date_to is not None:
        conditions.append("stream.start < %s + INTERVAL '1 day'")
        params.append(date_to)
    if min_messages is not None:
        conditions.append("stream.message_count >= %s")
        params.append(min_messages)

    where_sql = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where_sql, params


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
def select_all_streams_db(
    creator_id,
    offset,
    cursor,
    *,
    sort="start",
    dir="desc",
    title=None,
    date_from=None,
    date_to=None,
    min_messages=None,
):
    where_sql, params = _build_stream_filter(creator_id, title, date_from, date_to, min_messages)
    sort_col = _SORT_COLUMNS.get(sort, _SORT_COLUMNS["start"])
    direction = _DIR.get(dir, "DESC")

    # sort_col/direction come from the hardcoded whitelists above, never from raw input.
    query = f"""
    SELECT
        stream.id,
        display_name,
        TO_CHAR(start, 'YYYY-MM-DD HH24:MI:SS') AS start,
        TO_CHAR("end", 'YYYY-MM-DD HH24:MI:SS') AS "end",
        thumbnail_url,
        message_count
    FROM stream
    JOIN creator ON stream.creator_id = creator.id
    {where_sql}
    ORDER BY {sort_col} {direction} NULLS LAST, stream.id DESC
    LIMIT 20 OFFSET %s
    """
    cursor.execute(query, (*params, offset))
    return cursor.fetchall()


@with_cursor
def select_all_stream_count_db(creator_id, cursor, *, title=None, date_from=None, date_to=None, min_messages=None):
    where_sql, params = _build_stream_filter(creator_id, title, date_from, date_to, min_messages)
    query = f"SELECT COUNT(*) FROM stream {where_sql}"
    cursor.execute(query, tuple(params))
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
def select_stream_mentions_db(stream_id, limit, cursor):
    # Two independent GROUP BYs over one stream's messages: the most-mentioned chatters
    # (top `limit`), and the top directed mention pairs (hardcoded LIMIT 20 — `limit`
    # applies ONLY to the mentioned-list query, never to the pairs query). tagged_chatter_id
    # has no FK, so nicks resolve via correlated subqueries to avoid dropping rows whose
    # target chatter row is absent. Same access pattern as select_most_tagged_chatters_db.
    # The pairs query excludes NULL senders (message.chatter_id is nullable) so a NULL sender
    # group can't rank high and 500 the endpoint through the required-int MentionPair contract.
    cursor.execute(
        """
        SELECT tagged_chatter_id,
               (SELECT nick FROM chatter WHERE chatter.id = tagged_chatter_id),
               COUNT(*) AS mention_count
        FROM message
        WHERE stream_id = %s
        GROUP BY tagged_chatter_id
        HAVING tagged_chatter_id IS NOT NULL
        ORDER BY mention_count DESC
        LIMIT %s
        """,
        (stream_id, limit),
    )
    mentioned = cursor.fetchall()

    cursor.execute(
        """
        SELECT chatter_id,
               (SELECT nick FROM chatter WHERE chatter.id = chatter_id),
               tagged_chatter_id,
               (SELECT nick FROM chatter WHERE chatter.id = tagged_chatter_id),
               COUNT(*) AS pair_count
        FROM message
        WHERE stream_id = %s AND chatter_id IS NOT NULL AND tagged_chatter_id IS NOT NULL
        GROUP BY chatter_id, tagged_chatter_id
        ORDER BY pair_count DESC
        LIMIT 20
        """,
        (stream_id,),
    )
    pairs = cursor.fetchall()

    return mentioned, pairs


@with_cursor
def select_chatter_messages_on_stream_db(stream_id, chatter_id, cursor):
    cursor.execute(
        """
    SELECT mt.text FROM message m JOIN message_text mt ON mt.id = m.message_text_id
    WHERE m.stream_id = %s AND m.chatter_id = %s ORDER BY m.time ASC, m.id ASC
    """,
        (stream_id, chatter_id),
    )
    return cursor.fetchall()
