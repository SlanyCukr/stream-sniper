from .decorators import with_cursor


@with_cursor
def select_stream_metrics_db(stream_id, cursor):
    cursor.execute(
        """
        SELECT
            total_messages,
            unique_chatters,
            duration_seconds,
            messages_per_minute::double precision,
            peak_messages,
            TO_CHAR(peak_bucket_minute, 'YYYY-MM-DD"T"HH24:MI:SS'),
            new_chatters,
            returning_chatters
        FROM stream_metrics
        WHERE stream_id = %s
        """,
        (stream_id,),
    )
    return cursor.fetchone()


@with_cursor
def select_stream_header_db(stream_id, cursor):
    cursor.execute(
        """
        SELECT TO_CHAR(start, 'YYYY-MM-DD"T"HH24:MI:SS'), twitch_id::text
        FROM stream
        WHERE id = %s
        """,
        (stream_id,),
    )
    return cursor.fetchone()


@with_cursor
def select_creator_metrics_series_db(creator_id, limit, cursor):
    # Most-recent `limit` streams, returned ascending by start. message_count comes
    # from stream.message_count (always populated at ingest) — NOT
    # stream_metrics.total_messages, which is NULL for streams not yet rolled up.
    cursor.execute(
        """
        SELECT stream_id, title, start_str, duration_seconds, message_count,
               messages_per_minute, unique_chatters, new_chatters, returning_chatters
        FROM (
            SELECT
                s.id AS stream_id,
                s.title AS title,
                TO_CHAR(s.start, 'YYYY-MM-DD"T"HH24:MI:SS') AS start_str,
                s.start AS start_raw,
                sm.duration_seconds AS duration_seconds,
                s.message_count AS message_count,
                COALESCE(sm.messages_per_minute, 0)::double precision AS messages_per_minute,
                COALESCE(sm.unique_chatters, 0) AS unique_chatters,
                COALESCE(sm.new_chatters, 0) AS new_chatters,
                COALESCE(sm.returning_chatters, 0) AS returning_chatters
            FROM stream s
            LEFT JOIN stream_metrics sm ON sm.stream_id = s.id
            WHERE s.creator_id = %s
            ORDER BY s.start DESC, s.id DESC
            LIMIT %s
        ) sub
        ORDER BY start_raw ASC, stream_id ASC
        """,
        (creator_id, limit),
    )
    return cursor.fetchall()
