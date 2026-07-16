from psycopg2.extensions import connection as Connection
from psycopg2.extensions import cursor as Cursor

from stream_sniper.database.gateways.identity.records import CreatorListRow, CreatorSummaryRow, CreatorTopChatterRow

from ...core.decorators import with_cursor, with_cursor_connection


@with_cursor
def select_creator_twitch_user_id_db(
    cursor: Cursor,
    nick: str,
) -> int | str:
    cursor.execute("SELECT twitch_id FROM creator WHERE nick = %s", (nick,))
    row = cursor.fetchone()
    if row is None:
        raise TypeError(f"Creator {nick!r} has no Twitch identifier")
    value = row[0]
    if isinstance(value, (int, str)):
        return value
    raise TypeError("creator.twitch_id must be an integer or string")


@with_cursor
def select_creator_id_db(
    cursor: Cursor,
    nick: str,
) -> int | None:
    cursor.execute("SELECT id FROM creator WHERE nick = %s", (nick,))
    result = cursor.fetchone()
    if result:
        return int(result[0])
    return None


@with_cursor_connection
def find_or_insert_creator_id_db(
    cursor: Cursor,
    connection: Connection,
    nick: str,
    display_name: str,
    profile_image_url: str | None,
    twitch_user_id: int | str,
) -> int:
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
    cursor.execute(sql, (nick, display_name, profile_image_url, twitch_user_id, nick))
    connection.commit()

    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Creator insert returned no identifier for {nick!r}")
    return int(row[0])


@with_cursor
def select_creators_db(
    cursor: Cursor,
) -> list[CreatorListRow]:
    cursor.execute("SELECT id, display_name FROM creator")
    return [CreatorListRow(int(row[0]), str(row[1])) for row in cursor.fetchall()]


@with_cursor
def select_creator_summary_db(
    cursor: Cursor,
    creator_id: int,
) -> CreatorSummaryRow | None:
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
            c.id, c.nick, c.display_name, c.profile_image_url,
            c.twitch_id AS twitch_user_id,
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
    row = cursor.fetchone()
    return CreatorSummaryRow(*row) if row else None


@with_cursor
def select_creator_top_chatters_db(
    cursor: Cursor,
    creator_id: int,
    limit: int,
) -> list[CreatorTopChatterRow]:
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
    return [CreatorTopChatterRow(int(row[0]), str(row[1]), int(row[2])) for row in cursor.fetchall()]
