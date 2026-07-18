from psycopg2.extensions import connection as Connection
from psycopg2.extensions import cursor as Cursor

from stream_sniper.database.gateways.analytics.records import (
    CreatorReportRow,
    CreatorTrendRow,
    StreamHeaderRow,
    StreamMetricsRow,
)

from ...core.decorators import with_cursor, with_cursor_connection
from ...core.wire_format import to_char_wire


@with_cursor_connection
def touch_stream_rollup_version_db(cursor: Cursor, connection: Connection, stream_id: int) -> None:
    """Bump one stream's rollup version (``computed_at``) without recomputing its metrics.

    Targeted refreshes (e.g. the post-bot-classification copypasta/scene-event refresh)
    rewrite rollup-derived data that the API's rollup-versioned cache keys guard. Touching
    ``computed_at`` rolls every scene/stream cache key derived from it, so superseded
    entries age out instead of being served for their full TTL. ``now()`` matches the
    expression the metrics upsert itself writes.
    """
    cursor.execute(
        "UPDATE stream_metrics SET computed_at = now() WHERE stream_id = %s",
        (stream_id,),
    )
    connection.commit()


@with_cursor
def select_stream_metrics_db(
    cursor: Cursor,
    stream_id: int,
) -> StreamMetricsRow | None:
    cursor.execute(
        f"""
        SELECT
            total_messages,
            unique_chatters,
            duration_seconds,
            messages_per_minute::double precision,
            peak_messages,
            {to_char_wire("peak_bucket_minute")},
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
def select_stream_rollup_version_db(
    cursor: Cursor,
    stream_id: int,
) -> str | None:
    """Opaque rollup version for one stream (``None`` until first rollup).

    Used as a cache-key part so API responses derived from this stream's
    rollup tables invalidate when the collector/tracking process recomputes
    them. Epoch text keeps full precision; the value is never rendered.
    """
    cursor.execute(
        "SELECT EXTRACT(EPOCH FROM computed_at)::text FROM stream_metrics WHERE stream_id = %s",
        (stream_id,),
    )
    row = cursor.fetchone()
    return row[0] if row else None


@with_cursor
def select_stream_creator_rollup_version_db(
    cursor: Cursor,
    stream_id: int,
) -> str | None:
    """Latest rollup version across all streams of the given stream's creator.

    Covers responses that mix one stream with a creator-wide baseline
    (e.g. the stream report card): a rollup of ANY sibling stream changes
    the baseline, so the version must move with the whole creator.
    """
    cursor.execute(
        """
        SELECT EXTRACT(EPOCH FROM max(sm.computed_at))::text
        FROM stream_metrics sm
        JOIN stream s ON s.id = sm.stream_id
        WHERE s.creator_id = (SELECT creator_id FROM stream WHERE id = %s)
        """,
        (stream_id,),
    )
    row = cursor.fetchone()
    return row[0] if row else None


@with_cursor
def select_creator_rollup_version_db(
    cursor: Cursor,
    creator_id: int,
) -> str | None:
    """Latest rollup version across all streams of one creator."""
    cursor.execute(
        """
        SELECT EXTRACT(EPOCH FROM max(sm.computed_at))::text
        FROM stream_metrics sm
        JOIN stream s ON s.id = sm.stream_id
        WHERE s.creator_id = %s
        """,
        (creator_id,),
    )
    row = cursor.fetchone()
    return row[0] if row else None


@with_cursor
def select_scene_rollup_version_db(cursor: Cursor) -> str | None:
    """Latest rollup version across the whole scene (all streams)."""
    cursor.execute("SELECT EXTRACT(EPOCH FROM max(computed_at))::text FROM stream_metrics")
    row = cursor.fetchone()
    return row[0] if row else None


@with_cursor
def select_stream_header_db(
    cursor: Cursor,
    stream_id: int,
) -> StreamHeaderRow | None:
    cursor.execute(
        f"""
        SELECT {to_char_wire("start")}, twitch_id::text AS twitch_vod_id
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
        f"""
        SELECT stream_id, title, start_str, duration_seconds, message_count,
               messages_per_minute, unique_chatters, new_chatters, returning_chatters
        FROM (
            SELECT
                s.id AS stream_id,
                s.title AS title,
                {to_char_wire("s.start")} AS start_str,
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
        f"""
        SELECT stream_id, start_str, duration_seconds, total_messages, messages_per_minute,
               unique_chatters, new_chatters, returning_chatters, sub_messages, peak_messages
        FROM (
            SELECT
                s.id AS stream_id,
                {to_char_wire("s.start")} AS start_str,
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
