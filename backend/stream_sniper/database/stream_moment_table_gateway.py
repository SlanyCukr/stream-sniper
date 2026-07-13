"""Database gateway for stream_moment (persisted enriched moments) + its text sibling.

The rollup engine derives phrases and enriched moments in Python, then writes both
stream_phrase_stats and stream_moment together in ONE transaction (blueprint TX2) so a
reader never sees phrases without their moments. Human curation lives in the separate
moment_review table (moment_review_table_gateway) and is never touched here.
"""

from typing import List, Optional, Tuple

from psycopg2.extras import Json, execute_values

from .decorators import with_cursor, with_cursor_connection

# Hardcoded status whitelist: the caller-supplied status maps through this dict to a fixed
# SQL predicate, so no user string is ever interpolated into the query. "pending" means no
# moment_review row exists. An unrecognized/empty status yields no status filter (all moments).
_QUEUE_STATUS_CLAUSE = {
    "pending": "mr.status IS NULL",
    "bookmarked": "mr.status = 'bookmarked'",
    "rejected": "mr.status = 'rejected'",
    "clipped": "mr.status = 'clipped'",
    "published": "mr.status = 'published'",
}


@with_cursor
def select_stream_moments_db(stream_id, cursor):
    cursor.execute(
        """
        SELECT
            TO_CHAR(sm.bucket_minute, 'YYYY-MM-DD"T"HH24:MI:SS'),
            sm.offset_seconds,
            sm.message_count,
            sm.baseline::double precision,
            sm.ratio::double precision,
            sm.unique_chatters,
            sm.sub_share::double precision,
            sm.emote_share::double precision,
            sm.top_phrases,
            sm.sample_messages,
            mr.status,
            mr.clip_url,
            mr.note
        FROM stream_moment sm
        LEFT JOIN moment_review mr
            ON mr.stream_id = sm.stream_id AND mr.bucket_minute = sm.bucket_minute
        WHERE sm.stream_id = %s
        ORDER BY sm.bucket_minute ASC
        """,
        (stream_id,),
    )
    return cursor.fetchall()


@with_cursor
def select_moment_queue_db(status, creator_id, limit, offset, cursor):
    """Highlight-queue page: enriched moments with stream/creator context + review status.

    Returns (rows, total). Each row:
      (stream_id, title, start, twitch_id, creator_id, creator_display_name,
       bucket_minute, offset_seconds, message_count, baseline, ratio, unique_chatters,
       sub_share, emote_share, top_phrases, sample_messages, status, clip_url, note)
    where status is NULL for pending (no moment_review row). `status` filters through a
    hardcoded whitelist; `creator_id` (optional) restricts to one creator. Ordering places
    reviewed moments first by recency, then pending moments by spike ratio.
    """
    filters = []
    params: dict = {}

    status_clause = _QUEUE_STATUS_CLAUSE.get(status)
    if status_clause is not None:
        filters.append(status_clause)
    if creator_id is not None:
        filters.append("s.creator_id = %(creator_id)s")
        params["creator_id"] = creator_id

    where_sql = f"WHERE {' AND '.join(filters)}" if filters else ""

    cursor.execute(
        f"""
        SELECT count(*)
        FROM stream_moment sm
        JOIN stream s ON s.id = sm.stream_id
        LEFT JOIN moment_review mr
            ON mr.stream_id = sm.stream_id AND mr.bucket_minute = sm.bucket_minute
        {where_sql}
        """,
        params,
    )
    total = cursor.fetchone()[0]

    page_params = {**params, "limit": limit, "offset": offset}
    cursor.execute(
        f"""
        SELECT
            sm.stream_id,
            s.title,
            TO_CHAR(s.start, 'YYYY-MM-DD"T"HH24:MI:SS'),
            s.twitch_id::text,
            c.id,
            c.display_name,
            TO_CHAR(sm.bucket_minute, 'YYYY-MM-DD"T"HH24:MI:SS'),
            sm.offset_seconds,
            sm.message_count,
            sm.baseline::double precision,
            sm.ratio::double precision,
            sm.unique_chatters,
            sm.sub_share::double precision,
            sm.emote_share::double precision,
            sm.top_phrases,
            sm.sample_messages,
            mr.status,
            mr.clip_url,
            mr.note
        FROM stream_moment sm
        JOIN stream s ON s.id = sm.stream_id
        LEFT JOIN creator c ON c.id = s.creator_id
        LEFT JOIN moment_review mr
            ON mr.stream_id = sm.stream_id AND mr.bucket_minute = sm.bucket_minute
        {where_sql}
        ORDER BY mr.updated_at DESC NULLS LAST, sm.ratio DESC NULLS LAST,
                 sm.stream_id DESC, sm.bucket_minute DESC
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        page_params,
    )
    return cursor.fetchall(), total


@with_cursor
def select_moment_exists_db(stream_id, bucket_minute, cursor):
    """Return True if a stream_moment row exists for (stream_id, bucket_minute)."""
    cursor.execute(
        "SELECT 1 FROM stream_moment WHERE stream_id = %s AND bucket_minute = %s",
        (stream_id, bucket_minute),
    )
    return cursor.fetchone() is not None


@with_cursor_connection
def replace_stream_text_rollups_db(
    stream_id,
    phrase_rows: List[Tuple[str, int, int]],
    moment_rows: List[Tuple],
    cursor,
    connection,
):
    """Atomically replace this stream's phrase + moment rollups (blueprint TX2).

    phrase_rows: (phrase, usage_count, chatter_count).
    moment_rows: (bucket_minute, offset_seconds, message_count, baseline, ratio,
                  unique_chatters, sub_share, emote_share, top_phrases, sample_messages)
                 where top_phrases / sample_messages are JSON-serializable lists (or None).
    """
    cursor.execute("DELETE FROM stream_phrase_stats WHERE stream_id = %s", (stream_id,))
    cursor.execute("DELETE FROM stream_moment WHERE stream_id = %s", (stream_id,))

    if phrase_rows:
        execute_values(
            cursor,
            """
            INSERT INTO stream_phrase_stats (stream_id, phrase, usage_count, chatter_count)
            VALUES %s
            """,
            [(stream_id, phrase, usage, chatters) for phrase, usage, chatters in phrase_rows],
        )

    if moment_rows:
        execute_values(
            cursor,
            """
            INSERT INTO stream_moment (
                stream_id, bucket_minute, offset_seconds, message_count, baseline, ratio,
                unique_chatters, sub_share, emote_share, top_phrases, sample_messages)
            VALUES %s
            """,
            [_moment_values(stream_id, row) for row in moment_rows],
        )

    connection.commit()


def _moment_values(stream_id, row: Tuple):
    (
        bucket_minute,
        offset_seconds,
        message_count,
        baseline,
        ratio,
        unique_chatters,
        sub_share,
        emote_share,
        top_phrases,
        sample_messages,
    ) = row
    return (
        stream_id,
        bucket_minute,
        offset_seconds,
        message_count,
        baseline,
        ratio,
        unique_chatters,
        sub_share,
        emote_share,
        _json_or_none(top_phrases),
        _json_or_none(sample_messages),
    )


def _json_or_none(value) -> Optional[Json]:
    return Json(value) if value is not None else None
