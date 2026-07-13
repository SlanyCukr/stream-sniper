"""Small-table persistence and reads for deterministic scene events."""

from psycopg2.extras import Json, execute_values

from .decorators import with_cursor, with_cursor_connection


@with_cursor
def select_stream_event_signals_db(stream_id, cursor):
    cursor.execute(
        """
        SELECT s.id, s.creator_id, c.display_name, s.title,
               TO_CHAR(COALESCE(s."end", s.start), 'YYYY-MM-DD"T"HH24:MI:SS'),
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
    header = cursor.fetchone()

    cursor.execute(
        """
        SELECT TO_CHAR(sm.bucket_minute, 'YYYY-MM-DD"T"HH24:MI:SS'),
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
    moment = cursor.fetchone()

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
    return header, moment, cursor.fetchall()


@with_cursor_connection
def replace_stream_scene_events_db(stream_id, events, cursor, connection):
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
                    event["event_type"], event["occurred_at"], event["creator_id"],
                    stream_id, event.get("message_text_id"), event["title"],
                    event["summary"], Json(event.get("metadata", {})), event["dedupe_key"],
                )
                for event in events
            ],
        )
    connection.commit()


@with_cursor
def select_scene_events_db(days, event_type, creator_id, limit, offset, cursor):
    filters = ["se.occurred_at >= (now() AT TIME ZONE 'UTC') - (%s * interval '1 day')"]
    params = [days]
    if event_type:
        filters.append("se.event_type = %s")
        params.append(event_type)
    if creator_id is not None:
        filters.append("se.creator_id = %s")
        params.append(creator_id)
    where = " AND ".join(filters)
    cursor.execute(f"SELECT count(*) FROM scene_event se WHERE {where}", tuple(params))
    total = cursor.fetchone()[0]
    cursor.execute(
        f"""
        SELECT se.id, se.event_type,
               TO_CHAR(se.occurred_at, 'YYYY-MM-DD"T"HH24:MI:SS'),
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
    return cursor.fetchall(), total
