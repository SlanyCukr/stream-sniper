from psycopg2.extensions import cursor as Cursor

from stream_sniper.database.gateways.analytics.records import (
    CreatorReportRow,
    CreatorTrendRow,
    StreamHeaderRow,
    StreamMetricsRow,
)

from ...core.decorators import with_cursor


@with_cursor
def select_stream_metrics_db(
    cursor: Cursor,
    stream_id: int,
) -> StreamMetricsRow | None:
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
            returning_chatters,
            sub_messages,
            emote_messages
        FROM stream_metrics
        WHERE stream_id = %s
        """,
        (stream_id,),
    )
    row = cursor.fetchone()
    return StreamMetricsRow(*row) if row else None


@with_cursor
def select_stream_header_db(
    cursor: Cursor,
    stream_id: int,
) -> StreamHeaderRow | None:
    cursor.execute(
        """
        SELECT TO_CHAR(start, 'YYYY-MM-DD"T"HH24:MI:SS'), twitch_id::text AS twitch_vod_id
        FROM stream
        WHERE id = %s
        """,
        (stream_id,),
    )
    row = cursor.fetchone()
    return StreamHeaderRow(*row) if row else None


@with_cursor
def select_creator_metrics_series_db(
    cursor: Cursor,
    creator_id: int,
    limit: int,
) -> list[CreatorTrendRow]:
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
    return [CreatorTrendRow(*row) for row in cursor.fetchall()]


@with_cursor
def select_creator_report_series_db(
    cursor: Cursor,
    creator_id: int,
    limit: int,
) -> list[CreatorReportRow]:
    # Most-recent `limit` streams, returned ascending by start — same skeleton as
    # select_creator_metrics_series_db, but WITHOUT COALESCE: un-rolled-up streams
    # come back with NULL stream_metrics columns so report baseline math can
    # exclude them (nullable = unknown, never 0).
    cursor.execute(
        """
        SELECT stream_id, start_str, duration_seconds, total_messages, messages_per_minute,
               unique_chatters, new_chatters, returning_chatters, sub_messages, peak_messages
        FROM (
            SELECT
                s.id AS stream_id,
                TO_CHAR(s.start, 'YYYY-MM-DD"T"HH24:MI:SS') AS start_str,
                s.start AS start_raw,
                sm.duration_seconds AS duration_seconds,
                sm.total_messages AS total_messages,
                sm.messages_per_minute::double precision AS messages_per_minute,
                sm.unique_chatters AS unique_chatters,
                sm.new_chatters AS new_chatters,
                sm.returning_chatters AS returning_chatters,
                sm.sub_messages AS sub_messages,
                sm.peak_messages AS peak_messages
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
    return [CreatorReportRow(*row) for row in cursor.fetchall()]
