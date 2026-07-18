from typing import cast

from psycopg2.extensions import connection as Connection
from psycopg2.extensions import cursor as Cursor

from ...core.decorators import with_cursor, with_cursor_connection
from ...core.wire_format import to_char_wire
from .records import ChatterActiveStreamRow, ChatterDebutRow


@with_cursor
def select_stream_creator_id_db(
    cursor: Cursor,
    stream_id: int,
) -> tuple[int | None] | None:
    cursor.execute("SELECT creator_id FROM stream WHERE id = %s", (stream_id,))
    return cast(tuple[int | None] | None, cursor.fetchone())


@with_cursor
def select_rollup_stream_ids_db(
    cursor: Cursor,
    *,
    creator_nick: str | None = None,
    force: bool = False,
) -> list[tuple[int, int]]:
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
    return cast(list[tuple[int, int]], cursor.fetchall())


@with_cursor
def select_stream_ids_for_chatters_db(
    cursor: Cursor,
    chatter_ids: list[int],
) -> list[int]:
    """Distinct streams where any of the given chatters spoke, from the rollup (no message scan).

    Used after bot classification to target the copypasta/scene-event refresh at only
    the streams a newly-marked bot participated in.
    """
    if not chatter_ids:
        return []
    cursor.execute(
        """
        SELECT DISTINCT stream_id
        FROM stream_chatter_stats
        WHERE chatter_id = ANY(%s)
        ORDER BY stream_id ASC
        """,
        (chatter_ids,),
    )
    return [int(row[0]) for row in cursor.fetchall()]


@with_cursor
def select_chatter_debut_db(
    cursor: Cursor,
    chatter_id: int,
) -> ChatterDebutRow | None:
    """The chatter's first message in the corpus, from the stream_chatter_stats rollup.

    Ordered by the earliest per-stream first_message_time (NULLs excluded), so it is the
    actual first message rather than the first attended stream's start. No message scan.
    :return: A ChatterDebutRow, or None if the chatter has no recorded messages.
    """
    cursor.execute(
        f"""
        SELECT
            scs.stream_id,
            s.title,
            cr.display_name,
            {to_char_wire("scs.first_message_time")}
        FROM stream_chatter_stats scs
        JOIN stream s ON s.id = scs.stream_id
        JOIN creator cr ON cr.id = s.creator_id
        WHERE scs.chatter_id = %s AND scs.first_message_time IS NOT NULL
        ORDER BY scs.first_message_time ASC, scs.stream_id ASC
        LIMIT 1
        """,
        (chatter_id,),
    )
    row = cursor.fetchone()
    return ChatterDebutRow(*row) if row is not None else None


@with_cursor
def select_chatter_most_active_stream_db(
    cursor: Cursor,
    chatter_id: int,
) -> ChatterActiveStreamRow | None:
    """The single stream the chatter sent the most messages in.

    Reads only the stream_chatter_stats rollup; ties break on the lower stream id.
    :return: A ChatterActiveStreamRow, or None if the chatter has no recorded streams.
    """
    cursor.execute(
        """
        SELECT
            scs.stream_id,
            s.title,
            cr.display_name,
            scs.message_count
        FROM stream_chatter_stats scs
        JOIN stream s ON s.id = scs.stream_id
        JOIN creator cr ON cr.id = s.creator_id
        WHERE scs.chatter_id = %s
        ORDER BY scs.message_count DESC, scs.stream_id ASC
        LIMIT 1
        """,
        (chatter_id,),
    )
    row = cursor.fetchone()
    return ChatterActiveStreamRow(*row) if row is not None else None


def _replace_time_buckets(cursor: Cursor, params: dict[str, int | list[int]]) -> None:
    """Replace per-minute message, chatter, subscriber, and emote buckets."""
    cursor.execute("DELETE FROM stream_time_bucket WHERE stream_id = %(sid)s", params)
    cursor.execute(
        """
        INSERT INTO stream_time_bucket
            (stream_id, bucket_minute, message_count, unique_chatters, sub_messages, emote_messages)
        SELECT %(sid)s, date_trunc('minute', time), count(*), count(DISTINCT chatter_id),
               -- Era detection keys off count(is_subscriber): pre-0007 rows carry NULL metadata,
               -- so a bucket where NO message has a known is_subscriber is "unknown era" (NULL,
               -- not 0). emote_count shares the same collection era; `> 0` treats both the pre-0007
               -- NULL and the new known-zero (0) as "no emote", counting only real positives.
               CASE WHEN count(is_subscriber) = 0 THEN NULL
                    ELSE count(*) FILTER (WHERE is_subscriber IS TRUE) END,
               CASE WHEN count(is_subscriber) = 0 THEN NULL
                    ELSE count(*) FILTER (WHERE emote_count > 0) END
        FROM message
        WHERE stream_id = %(sid)s AND time IS NOT NULL
        GROUP BY date_trunc('minute', time)
        """,
        params,
    )


def _select_stream_chatter_ids(cursor: Cursor, params: dict[str, int | list[int]]) -> list[int]:
    """Chatters currently recorded for the stream (before a rollup replace)."""
    cursor.execute("SELECT chatter_id FROM stream_chatter_stats WHERE stream_id = %(sid)s", params)
    return [int(row[0]) for row in cursor.fetchall()]


def _replace_stream_chatter_stats(cursor: Cursor, params: dict[str, int | list[int]]) -> None:
    """Replace per-chatter aggregates for the stream."""
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


def _replace_stream_metrics(cursor: Cursor, params: dict[str, int | list[int]]) -> None:
    """Replace the single stream summary row from the preceding phase tables."""
    cursor.execute("DELETE FROM stream_metrics WHERE stream_id = %(sid)s", params)
    cursor.execute(
        """
        INSERT INTO stream_metrics (
            stream_id, total_messages, unique_chatters, duration_seconds,
            messages_per_minute, peak_messages, peak_bucket_minute,
            new_chatters, returning_chatters, sub_messages, emote_messages, computed_at)
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
            meta.sub_messages,
            meta.emote_messages,
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
        CROSS JOIN
            -- NULL (unknown) when EVERY bucket's value is NULL (all pre-0007), else the sum of the
            -- known buckets (SUM ignores NULLs). count(col)=0 means no bucket had a known value.
            (SELECT CASE WHEN count(sub_messages) = 0 THEN NULL
                         ELSE sum(sub_messages)::int END AS sub_messages,
                    CASE WHEN count(emote_messages) = 0 THEN NULL
                         ELSE sum(emote_messages)::int END AS emote_messages
             FROM stream_time_bucket WHERE stream_id = %(sid)s) meta
        """,
        params,
    )


def _upsert_creator_chatter_stats(cursor: Cursor, params: dict[str, int | list[int]]) -> None:
    """Refresh creator aggregates for chatters touched by the stream.

    The refresh set is the union of the stream's current chatters and the
    chatters recorded before the replace (``%(prev)s``): if a re-collection or
    cleanup removed a chatter from this stream, their creator-level aggregates
    are recomputed from the remaining streams instead of staying stale forever.
    Chatters with no remaining rows for the creator produce no INSERT row (the
    LATERAL first/last-seen lookups are empty); those are handled by
    ``_delete_orphaned_creator_chatter_stats``.
    """
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
        FROM (
            SELECT chatter_id FROM stream_chatter_stats WHERE stream_id = %(sid)s
            UNION
            SELECT unnest(%(prev)s::int[])
        ) t
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


def _delete_orphaned_creator_chatter_stats(cursor: Cursor, params: dict[str, int | list[int]]) -> None:
    """Drop creator aggregates for previous chatters with no remaining streams.

    Complements ``_upsert_creator_chatter_stats``: a chatter removed from this
    stream by a re-collection who attended no other stream of the creator would
    otherwise keep a stale creator_chatter_stats row forever.
    """
    cursor.execute(
        """
        DELETE FROM creator_chatter_stats ccs
        WHERE ccs.creator_id = %(cid)s
          AND ccs.chatter_id = ANY(%(prev)s::int[])
          AND NOT EXISTS (
              SELECT 1
              FROM stream_chatter_stats scs
              JOIN stream s ON s.id = scs.stream_id
              WHERE scs.chatter_id = ccs.chatter_id AND s.creator_id = %(cid)s
          )
        """,
        params,
    )


def _replace_stream_emote_stats(cursor: Cursor, params: dict[str, int | list[int]]) -> None:
    """Replace case-sensitive, name-deduplicated per-stream emote usage."""
    cursor.execute("DELETE FROM stream_emote_stats WHERE stream_id = %(sid)s", params)
    cursor.execute(
        r"""
        INSERT INTO stream_emote_stats (stream_id, emote_id, usage_count, chatter_count)
        SELECT %(sid)s, d.id, count(*), count(DISTINCT m.chatter_id)
        FROM message m
        JOIN message_text mt ON mt.id = m.message_text_id
        CROSS JOIN LATERAL regexp_split_to_table(mt.text, '\s+') AS w(word)
        JOIN (
            SELECT DISTINCT ON (name) id, name
            FROM emote_dictionary
            WHERE length(name) >= 3
            ORDER BY name, CASE source WHEN 'twitch' THEN 0 ELSE 1 END
        ) d ON d.name = w.word
        -- Guard for very large streams: no dictionary name is < 3 or > 64 chars, so filtering the
        -- split words by length shrinks the intermediate before the join without changing results.
        WHERE m.stream_id = %(sid)s AND length(w.word) BETWEEN 3 AND 64
        GROUP BY d.id
        """,
        params,
    )


@with_cursor_connection
def recompute_stream_rollup_db(
    cursor: Cursor,
    connection: Connection,
    stream_id: int,
    creator_id: int,
) -> None:
    """Recompute the SQL rollup phases atomically and idempotently."""
    params: dict[str, int | list[int]] = {"sid": stream_id, "cid": creator_id}
    _replace_time_buckets(cursor, params)
    params["prev"] = _select_stream_chatter_ids(cursor, params)
    _replace_stream_chatter_stats(cursor, params)
    _replace_stream_metrics(cursor, params)
    _upsert_creator_chatter_stats(cursor, params)
    _delete_orphaned_creator_chatter_stats(cursor, params)
    _replace_stream_emote_stats(cursor, params)
    connection.commit()
