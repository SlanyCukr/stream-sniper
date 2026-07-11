from .decorators import with_cursor, with_cursor_connection


@with_cursor
def select_stream_creator_id_db(stream_id, cursor):
    cursor.execute("SELECT creator_id FROM stream WHERE id = %s", (stream_id,))
    return cursor.fetchone()


@with_cursor
def select_rollup_stream_ids_db(cursor, *, creator_nick=None, force=False):
    # Streams selected for the backfill, chronological per-creator so new/returning
    # counts are computed in the correct order. Without --force, streams that already
    # have a stream_metrics row are skipped (fast gap-fill resume).
    where = []
    params = []
    if creator_nick is not None:
        where.append("cr.nick = %s")
        params.append(creator_nick)
    if not force:
        where.append("sm.stream_id IS NULL")

    sql = """
        SELECT s.id, s.creator_id
        FROM stream s
        JOIN creator cr ON cr.id = s.creator_id
        LEFT JOIN stream_metrics sm ON sm.stream_id = s.id
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY s.creator_id, s.start ASC, s.id ASC"

    cursor.execute(sql, tuple(params))
    return cursor.fetchall()


@with_cursor_connection
def recompute_stream_rollup_db(stream_id, creator_id, cursor, connection):
    """Recompute all rollups for one stream in a single transaction (idempotent).

    Runs statements (a)-(d) from MASTER_PLAN §4.2 in order, then commits:
      (a) stream_time_bucket, (b) stream_chatter_stats, (c) stream_metrics,
      (d) creator_chatter_stats. Every statement is a DELETE+INSERT / UPSERT recompute,
      so re-running with unchanged message data yields identical results.
    """
    params = {"sid": stream_id, "cid": creator_id}

    # (a) per-minute buckets
    cursor.execute("DELETE FROM stream_time_bucket WHERE stream_id = %(sid)s", params)
    cursor.execute(
        """
        INSERT INTO stream_time_bucket (stream_id, bucket_minute, message_count, unique_chatters)
        SELECT %(sid)s, date_trunc('minute', time), count(*), count(DISTINCT chatter_id)
        FROM message
        WHERE stream_id = %(sid)s AND time IS NOT NULL
        GROUP BY date_trunc('minute', time)
        """,
        params,
    )

    # (b) per-chatter aggregates for this stream
    cursor.execute("DELETE FROM stream_chatter_stats WHERE stream_id = %(sid)s", params)
    cursor.execute(
        """
        INSERT INTO stream_chatter_stats
            (stream_id, chatter_id, message_count, first_message_time, last_message_time)
        SELECT %(sid)s, chatter_id, count(*), min(time), max(time)
        FROM message
        WHERE stream_id = %(sid)s AND chatter_id IS NOT NULL
        GROUP BY chatter_id
        """,
        params,
    )

    # (c) one summary row per stream (exactly one, even with zero buckets/chatters)
    cursor.execute("DELETE FROM stream_metrics WHERE stream_id = %(sid)s", params)
    cursor.execute(
        """
        INSERT INTO stream_metrics (
            stream_id, total_messages, unique_chatters, duration_seconds,
            messages_per_minute, peak_messages, peak_bucket_minute,
            new_chatters, returning_chatters, computed_at)
        SELECT
            %(sid)s,
            agg.total_messages,
            agg.unique_chatters,
            dur.duration_seconds,
            CASE WHEN dur.duration_seconds > 0
                 THEN round(agg.total_messages * 60.0 / dur.duration_seconds, 2)
                 ELSE NULL END,
            COALESCE((SELECT message_count FROM stream_time_bucket
                      WHERE stream_id = %(sid)s
                      ORDER BY message_count DESC, bucket_minute ASC LIMIT 1), 0),
            (SELECT bucket_minute FROM stream_time_bucket
             WHERE stream_id = %(sid)s
             ORDER BY message_count DESC, bucket_minute ASC LIMIT 1),
            nc.new_chatters,
            agg.unique_chatters - nc.new_chatters,
            now()
        FROM
            (SELECT COALESCE(sum(message_count), 0)::int AS total_messages,
                    count(*)::int AS unique_chatters
             FROM stream_chatter_stats WHERE stream_id = %(sid)s) agg
        CROSS JOIN
            (SELECT CASE WHEN "end" IS NULL THEN NULL
                         ELSE GREATEST(EXTRACT(EPOCH FROM ("end" - start))::int, 0) END
                    AS duration_seconds
             FROM stream WHERE id = %(sid)s) dur
        CROSS JOIN
            (SELECT count(*)::int AS new_chatters
             FROM stream_chatter_stats scs
             WHERE scs.stream_id = %(sid)s
               AND NOT EXISTS (
                   SELECT 1
                   FROM stream_chatter_stats scs2
                   JOIN stream ps ON ps.id = scs2.stream_id
                   WHERE scs2.chatter_id = scs.chatter_id
                     AND ps.creator_id = %(cid)s
                     AND (ps.start, ps.id) < (
                         (SELECT start FROM stream WHERE id = %(sid)s), %(sid)s)
               )) nc
        """,
        params,
    )

    # (d) per-creator per-chatter aggregates for the chatters touched by this stream
    cursor.execute(
        """
        INSERT INTO creator_chatter_stats (
            creator_id, chatter_id, streams_attended, total_messages,
            first_seen_stream_id, first_seen_at, last_seen_stream_id, last_seen_at, updated_at)
        SELECT
            %(cid)s,
            t.chatter_id,
            agg.streams_attended,
            agg.total_messages,
            fs.stream_id, fs.start,
            ls.stream_id, ls.start,
            now()
        FROM (SELECT DISTINCT chatter_id FROM stream_chatter_stats WHERE stream_id = %(sid)s) t
        CROSS JOIN LATERAL (
            SELECT count(*)::int AS streams_attended,
                   COALESCE(sum(scs.message_count), 0)::bigint AS total_messages
            FROM stream_chatter_stats scs
            JOIN stream s ON s.id = scs.stream_id
            WHERE scs.chatter_id = t.chatter_id AND s.creator_id = %(cid)s
        ) agg
        CROSS JOIN LATERAL (
            SELECT s.id AS stream_id, s.start
            FROM stream_chatter_stats scs
            JOIN stream s ON s.id = scs.stream_id
            WHERE scs.chatter_id = t.chatter_id AND s.creator_id = %(cid)s
            ORDER BY s.start ASC, s.id ASC LIMIT 1
        ) fs
        CROSS JOIN LATERAL (
            SELECT s.id AS stream_id, s.start
            FROM stream_chatter_stats scs
            JOIN stream s ON s.id = scs.stream_id
            WHERE scs.chatter_id = t.chatter_id AND s.creator_id = %(cid)s
            ORDER BY s.start DESC, s.id DESC LIMIT 1
        ) ls
        ON CONFLICT (creator_id, chatter_id) DO UPDATE SET
            streams_attended = EXCLUDED.streams_attended,
            total_messages = EXCLUDED.total_messages,
            first_seen_stream_id = EXCLUDED.first_seen_stream_id,
            first_seen_at = EXCLUDED.first_seen_at,
            last_seen_stream_id = EXCLUDED.last_seen_stream_id,
            last_seen_at = EXCLUDED.last_seen_at,
            updated_at = EXCLUDED.updated_at
        """,
        params,
    )

    connection.commit()
