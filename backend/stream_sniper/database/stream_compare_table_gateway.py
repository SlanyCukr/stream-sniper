"""Bounded rollup queries for comparing two to four streams."""

from .decorators import with_cursor


@with_cursor
def select_stream_compare_headers_db(stream_ids, cursor):
    cursor.execute(
        """
        SELECT
            s.id, s.creator_id, c.nick, c.display_name, s.title,
            TO_CHAR(s.start, 'YYYY-MM-DD"T"HH24:MI:SS'),
            sm.duration_seconds, sm.total_messages, sm.messages_per_minute,
            sm.unique_chatters, sm.new_chatters, sm.returning_chatters,
            sm.sub_messages, sm.emote_messages, sm.peak_messages,
            TO_CHAR(sm.peak_bucket_minute, 'YYYY-MM-DD"T"HH24:MI:SS')
        FROM stream s
        JOIN creator c ON c.id = s.creator_id
        LEFT JOIN stream_metrics sm ON sm.stream_id = s.id
        WHERE s.id = ANY(%s)
        """,
        (stream_ids,),
    )
    return cursor.fetchall()


@with_cursor
def select_stream_compare_buckets_db(stream_ids, cursor):
    cursor.execute(
        """
        SELECT stb.stream_id,
               TO_CHAR(stb.bucket_minute, 'YYYY-MM-DD"T"HH24:MI:SS'),
               stb.message_count, stb.unique_chatters
        FROM stream_time_bucket stb
        WHERE stb.stream_id = ANY(%s)
        ORDER BY stb.stream_id, stb.bucket_minute
        """,
        (stream_ids,),
    )
    return cursor.fetchall()


@with_cursor
def select_stream_pair_retention_db(stream_ids, cursor):
    """Audience overlap for each adjacent pair in the caller's chosen order."""
    cursor.execute(
        """
        WITH requested AS (
            SELECT stream_id, ordinal::int
            FROM unnest(%s::int[]) WITH ORDINALITY AS r(stream_id, ordinal)
        ), pairs AS (
            SELECT a.stream_id AS from_id, b.stream_id AS to_id
            FROM requested a
            JOIN requested b ON b.ordinal = a.ordinal + 1
        )
        SELECT p.from_id, p.to_id,
               (SELECT count(*) FROM stream_chatter_stats WHERE stream_id = p.from_id) AS from_size,
               (SELECT count(*) FROM stream_chatter_stats WHERE stream_id = p.to_id) AS to_size,
               (SELECT count(*)
                FROM stream_chatter_stats a
                JOIN stream_chatter_stats b ON b.chatter_id = a.chatter_id
                JOIN chatter ch ON ch.id = a.chatter_id
                WHERE a.stream_id = p.from_id AND b.stream_id = p.to_id
                  AND ch.is_bot IS NOT TRUE) AS retained
        FROM pairs p
        """,
        (stream_ids,),
    )
    return cursor.fetchall()
