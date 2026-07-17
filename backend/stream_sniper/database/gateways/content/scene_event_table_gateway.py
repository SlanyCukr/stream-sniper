"""Small-table persistence and reads for deterministic scene events."""

from collections.abc import Sequence

from psycopg2.extensions import connection as Connection
from psycopg2.extensions import cursor as Cursor
from psycopg2.extras import Json, execute_values

from stream_sniper.database.gateways.content.records import (
    SceneCopypastaSignalRow,
    SceneEventRow,
    SceneEventWrite,
    SceneMomentSignalRow,
    SceneSignalHeaderRow,
)

from ...core.decorators import with_cursor, with_cursor_connection
from ...core.wire_format import to_char_wire


@with_cursor
def select_stream_event_signals_db(
    cursor: Cursor,
    stream_id: int,
) -> tuple[SceneSignalHeaderRow | None, SceneMomentSignalRow | None, list[SceneCopypastaSignalRow]]:
    cursor.execute(
        f"""
        SELECT s.id, s.creator_id, c.display_name, s.title,
               {to_char_wire('COALESCE(s."end", s.start)')},
               sm.total_messages, sm.unique_chatters, sm.messages_per_minute,
               (SELECT max(pm.total_messages)
                FROM stream_metrics pm JOIN stream ps ON ps.id = pm.stream_id
                WHERE ps.creator_id = s.creator_id AND (ps.start, ps.id) < (s.start, s.id)),
               (SELECT max(pm.unique_chatters)
                FROM stream_metrics pm JOIN stream ps ON ps.id = pm.stream_id
                WHERE ps.creator_id = s.creator_id AND (ps.start, ps.id) < (s.start, s.id)),
               (SELECT max(pm.messages_per_minute)
                FROM stream_metrics pm JOIN stream ps ON ps.id = pm.stream_id
                WHERE ps.creator_id = s.creator_id AND (ps.start, ps.id) < (s.start, s.id))
        FROM stream s
        JOIN creator c ON c.id = s.creator_id
        LEFT JOIN stream_metrics sm ON sm.stream_id = s.id
        WHERE s.id = %s
        """,
        (stream_id,),
    )
    header_raw = cursor.fetchone()
    header = SceneSignalHeaderRow(*header_raw) if header_raw else None

    cursor.execute(
        f"""
        SELECT {to_char_wire("sm.bucket_minute")},
               sm.ratio::double precision, sm.message_count
        FROM stream_moment sm
        LEFT JOIN moment_review mr
          ON mr.stream_id = sm.stream_id AND mr.bucket_minute = sm.bucket_minute
        WHERE sm.stream_id = %s AND mr.status IS DISTINCT FROM 'rejected'
        ORDER BY sm.ratio DESC NULLS LAST, sm.bucket_minute
        LIMIT 1
        """,
        (stream_id,),
    )
    moment_raw = cursor.fetchone()
    moment = SceneMomentSignalRow(*moment_raw) if moment_raw else None

    cursor.execute(
        """
        SELECT scs.message_text_id, mt.text, scs.usage_count,
               (SELECT count(DISTINCT os.creator_id)
                FROM stream_copypasta_stats o
                JOIN stream os ON os.id = o.stream_id
                WHERE o.message_text_id = scs.message_text_id) AS creator_count
        FROM stream_copypasta_stats scs
        JOIN message_text mt ON mt.id = scs.message_text_id
        WHERE scs.stream_id = %s
          AND EXISTS (
              SELECT 1 FROM stream_copypasta_stats earlier
              JOIN stream es ON es.id = earlier.stream_id
              JOIN stream current_stream ON current_stream.id = scs.stream_id
              WHERE earlier.message_text_id = scs.message_text_id
                AND es.creator_id <> current_stream.creator_id
                AND (earlier.first_seen, earlier.stream_id) < (scs.first_seen, scs.stream_id)
          )
        ORDER BY creator_count DESC, scs.usage_count DESC
        LIMIT 3
        """,
        (stream_id,),
    )
    return header, moment, [SceneCopypastaSignalRow(*row) for row in cursor.fetchall()]


@with_cursor_connection
def replace_stream_scene_events_db(
    cursor: Cursor,
    connection: Connection,
    stream_id: int,
    events: Sequence[SceneEventWrite],
) -> None:
    cursor.execute("DELETE FROM scene_event WHERE stream_id = %s", (stream_id,))
    if events:
        execute_values(
            cursor,
            """
            INSERT INTO scene_event
                (event_type, occurred_at, creator_id, stream_id, message_text_id,
                 title, summary, metadata, dedupe_key)
            VALUES %s
            ON CONFLICT (dedupe_key) DO UPDATE SET
                occurred_at = EXCLUDED.occurred_at,
                title = EXCLUDED.title,
                summary = EXCLUDED.summary,
                metadata = EXCLUDED.metadata
            """,
            [
                (
                    event["event_type"],
                    event["occurred_at"],
                    event["creator_id"],
                    stream_id,
                    event["message_text_id"],
                    event["title"],
                    event["summary"],
                    Json(event["metadata"]),
                    event["dedupe_key"],
                )
                for event in events
            ],
        )
    connection.commit()


@with_cursor
def select_scene_events_db(
    cursor: Cursor,
    days: int,
    event_type: str | None,
    creator_id: int | None,
    limit: int,
    offset: int,
) -> tuple[list[SceneEventRow], int]:
    filters = ["se.occurred_at >= (now() AT TIME ZONE 'UTC') - (%s * interval '1 day')"]
    params: list[object] = [days]
    if event_type:
        filters.append("se.event_type = %s")
        params.append(event_type)
    if creator_id is not None:
        filters.append("se.creator_id = %s")
        params.append(creator_id)
    where = " AND ".join(filters)
    cursor.execute(f"SELECT count(*) FROM scene_event se WHERE {where}", tuple(params))
    total_row = cursor.fetchone()
    if total_row is None:
        raise RuntimeError("scene event count returned no row")
    total = int(total_row[0])
    cursor.execute(
        f"""
        SELECT se.id, se.event_type,
               {to_char_wire("se.occurred_at")},
               se.creator_id, c.nick, c.display_name, se.stream_id, se.message_text_id,
               se.title, se.summary, se.metadata
        FROM scene_event se
        LEFT JOIN creator c ON c.id = se.creator_id
        WHERE {where}
        ORDER BY se.occurred_at DESC, se.id DESC
        LIMIT %s OFFSET %s
        """,
        tuple(params) + (limit, offset),
    )
    return [SceneEventRow(*row) for row in cursor.fetchall()], total
