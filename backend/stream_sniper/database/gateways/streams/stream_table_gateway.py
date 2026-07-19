from datetime import date, datetime
from typing import cast

from psycopg2.extensions import connection as Connection
from psycopg2.extensions import cursor as Cursor

from stream_sniper.database.gateways.streams.records import (
    ChatterMessageTextRow,
    CreatorStreamSummaryRow,
    MentionedChatterRow,
    MentionPairRow,
    OtherCreatorRow,
    RankedChatterRow,
    StreamComprehensiveRow,
    StreamListRow,
    StreamParticipantRow,
)

from ...core.decorators import with_cursor, with_cursor_connection
from ...core.query_ordering import sql_direction

# Hardcoded whitelists — user-supplied ordering values map through these fixed
# fragments so no request string is ever interpolated into SQL. FastAPI validates
# the values with Query(pattern=...) before they reach the gateway; the .get()
# fallbacks keep any direct caller safe as well.
_SORT_COLUMNS = {
    "start": "stream.start",
    "message_count": "stream.message_count",
    "duration": 'EXTRACT(EPOCH FROM (stream."end" - stream.start))',
}

# ``stream.twitch_id`` is the deployed legacy column name. At the Python
# boundary the value is always named ``twitch_vod_id`` because it identifies an
# archived VOD, not a live Twitch stream session.


def _build_stream_filter(
    creator_id: int,
    title: str | None,
    date_from: date | None,
    date_to: date | None,
    min_messages: int | None,
) -> tuple[str, list[object]]:
    """Build the shared WHERE clause + params for stream listing and its COUNT(*).

    Both select_stream_page_db and count_streams_db route through this so the
    filtered rows and the filtered count (which feeds the pagination total) can never diverge.
    Returns (where_sql, params) where where_sql is "" or "WHERE ...".
    """
    conditions: list[str] = []
    params: list[object] = []

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
def stream_exists_by_twitch_vod_id_db(
    cursor: Cursor,
    twitch_vod_id: int | str,
) -> bool:
    cursor.execute("SELECT 1 FROM stream WHERE twitch_id = %s", (twitch_vod_id,))
    return cursor.fetchone() is not None


@with_cursor
def select_stream_page_db(
    cursor: Cursor,
    creator_id: int,
    offset: int,
    limit: int = 20,
    *,
    sort: str = "start",
    direction: str = "desc",
    title: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    min_messages: int | None = None,
) -> list[StreamListRow]:
    where_sql, params = _build_stream_filter(creator_id, title, date_from, date_to, min_messages)
    sort_col = _SORT_COLUMNS.get(sort, _SORT_COLUMNS["start"])
    sql_order = sql_direction(direction)

    # sort_col/sql_order come from the hardcoded whitelists above, never from raw input.
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
    ORDER BY {sort_col} {sql_order} NULLS LAST, stream.id DESC
    LIMIT %s OFFSET %s
    """
    cursor.execute(query, (*params, limit, offset))
    return [StreamListRow(*row) for row in cursor.fetchall()]


@with_cursor
def count_streams_db(
    cursor: Cursor,
    creator_id: int,
    *,
    title: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    min_messages: int | None = None,
) -> int:
    where_sql, params = _build_stream_filter(creator_id, title, date_from, date_to, min_messages)
    query = f"SELECT COUNT(*) FROM stream {where_sql}"
    cursor.execute(query, tuple(params))
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("Stream count query returned no row")
    return cast(int, row[0])


@with_cursor_connection
def insert_stream_db(
    cursor: Cursor,
    connection: Connection,
    twitch_vod_id: int | str,
    start: datetime,
    creator_id: int,
    title: str,
    stopped_at: datetime | None,
    thumbnail_url: str | None,
) -> int:
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
    cursor.execute(sql, (twitch_vod_id, start, creator_id, title, stopped_at, thumbnail_url, twitch_vod_id))
    connection.commit()

    row = cursor.fetchone()
    if row is None:
        raise RuntimeError(f"Stream insert returned no identifier for Twitch VOD {twitch_vod_id}")
    return cast(int, row[0])


@with_cursor_connection
def update_stream_message_count_db(
    cursor: Cursor,
    connection: Connection,
    stream_id: int,
    message_count: int,
) -> None:
    cursor.execute("UPDATE stream SET message_count = %s WHERE id = %s", (message_count, stream_id))
    connection.commit()


@with_cursor
def select_stream_comprehensive_db(
    cursor: Cursor,
    stream_id: int,
) -> StreamComprehensiveRow | None:
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
    row = cursor.fetchone()
    return StreamComprehensiveRow(*row) if row else None


@with_cursor
def select_most_active_chatters_db(
    cursor: Cursor,
    stream_id: int,
) -> list[RankedChatterRow]:
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
    return [RankedChatterRow(*row) for row in cursor.fetchall()]


@with_cursor
def select_most_tagged_chatters_db(
    cursor: Cursor,
    stream_id: int,
) -> list[RankedChatterRow]:
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
    return [RankedChatterRow(*row) for row in cursor.fetchall()]


@with_cursor
def select_creators_that_wrote_in_stream_db(
    cursor: Cursor,
    stream_id: int,
    creator_id: int,
) -> list[OtherCreatorRow]:
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
    return [OtherCreatorRow(*row) for row in cursor.fetchall()]


@with_cursor
def select_chatters_in_stream_db(
    cursor: Cursor,
    stream_id: int,
) -> list[StreamParticipantRow]:
    cursor.execute(
        """
    SELECT DISTINCT(chatter_id), (SELECT nick FROM chatter WHERE chatter.id = chatter_id ) FROM message WHERE stream_id = %s
    """,
        (stream_id,),
    )
    return [StreamParticipantRow(*row) for row in cursor.fetchall()]


@with_cursor
def select_stream_mentions_db(
    cursor: Cursor,
    stream_id: int,
    limit: int,
) -> tuple[list[MentionedChatterRow], list[MentionPairRow]]:
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
    mentioned = [MentionedChatterRow(*row) for row in cursor.fetchall()]

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
    pairs = [MentionPairRow(*row) for row in cursor.fetchall()]

    return mentioned, pairs


@with_cursor
def select_chatter_messages_on_stream_db(
    cursor: Cursor,
    stream_id: int,
    chatter_id: int,
) -> list[ChatterMessageTextRow]:
    cursor.execute(
        """
    SELECT mt.text FROM message m JOIN message_text mt ON mt.id = m.message_text_id
    WHERE m.stream_id = %s AND m.chatter_id = %s ORDER BY m.time ASC, m.id ASC
    """,
        (stream_id, chatter_id),
    )
    return [ChatterMessageTextRow(*row) for row in cursor.fetchall()]


@with_cursor
def select_creator_stream_summaries_db(
    cursor: Cursor,
    creator_ids: list[int],
) -> list[CreatorStreamSummaryRow]:
    """Batched per-creator collection summary for the admin tracking table.

    One query for the whole page of tracked streamers — avoids N+1 when the
    admin list renders last-collected-stream info per row.
    """
    if not creator_ids:
        return []
    cursor.execute(
        """
    SELECT creator_id, COUNT(*), MAX(start)
    FROM stream_sniper.stream
    WHERE creator_id = ANY(%s)
    GROUP BY creator_id
    """,
        (creator_ids,),
    )
    return [CreatorStreamSummaryRow(*row) for row in cursor.fetchall()]
