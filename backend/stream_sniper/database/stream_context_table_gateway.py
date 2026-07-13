"""Live stream context snapshots and VOD-time-window linkage."""

from psycopg2.extras import Json

from ..logging_config import get_logger
from .connection_pool import get_pool
from .decorators import log_database_operation, with_cursor

logger = get_logger(__name__)


@log_database_operation
def insert_stream_context_sample_db(
    tracked_streamer_id, twitch_stream_session_id, sampled_at, session_started_at,
    title, category_id, category_name, language, tags, is_mature,
) -> bool:
    """Persist a context snapshot without ever disrupting the monitor loop."""
    try:
        with get_pool().get_cursor(commit=True) as cursor:
            cursor.execute(
                """
                INSERT INTO stream_sniper.stream_context_sample
                    (tracked_streamer_id, twitch_stream_session_id, sampled_at,
                     session_started_at, title, category_id, category_name,
                     language, tags, is_mature)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (tracked_streamer_id, twitch_stream_session_id, sampled_at)
                DO NOTHING
                """,
                (
                    tracked_streamer_id, twitch_stream_session_id, sampled_at,
                    session_started_at, title, category_id, category_name,
                    language, Json(tags) if tags is not None else None, is_mature,
                ),
            )
        return True
    except Exception as exc:
        logger.error(
            f"Error inserting stream context for tracked_streamer_id={tracked_streamer_id}, "
            f"session={twitch_stream_session_id}: {exc}"
        )
        return False


@with_cursor
def select_stream_context_changes_db(stream_id, cursor):
    """Return only changed context states linked to a stored VOD by creator/time."""
    cursor.execute(
        """
        WITH tgt AS (
            SELECT s.creator_id, s.start AS s_start,
                   s.start - interval '10 minutes' AS win_start,
                   COALESCE(s."end", s.start + interval '12 hours') + interval '30 minutes' AS win_end
            FROM stream s WHERE s.id = %s
        ), windowed AS (
            SELECT scs.*
            FROM stream_context_sample scs
            JOIN tracked_streamers ts ON ts.id = scs.tracked_streamer_id
            JOIN tgt t ON t.creator_id = ts.creator_id
            WHERE scs.sampled_at AT TIME ZONE 'UTC' BETWEEN t.win_start AND t.win_end
        ), best_session AS (
            SELECT w.twitch_stream_session_id
            FROM windowed w CROSS JOIN tgt t
            WHERE w.session_started_at IS NOT NULL
              AND abs(EXTRACT(EPOCH FROM
                  (w.session_started_at AT TIME ZONE 'UTC' - t.s_start))) <= 900
            GROUP BY w.twitch_stream_session_id
            ORDER BY min(abs(EXTRACT(EPOCH FROM
                (w.session_started_at AT TIME ZONE 'UTC' - t.s_start))))
            LIMIT 1
        ), selected AS (
            SELECT w.* FROM windowed w
            WHERE NOT EXISTS (SELECT 1 FROM best_session)
               OR w.twitch_stream_session_id = (SELECT twitch_stream_session_id FROM best_session)
        ), states AS (
            SELECT s.*, row_number() OVER (ORDER BY sampled_at, id) AS rn,
                   lag(title) OVER (ORDER BY sampled_at, id) AS previous_title,
                   lag(category_id) OVER (ORDER BY sampled_at, id) AS previous_category_id,
                   lag(language) OVER (ORDER BY sampled_at, id) AS previous_language,
                   lag(tags) OVER (ORDER BY sampled_at, id) AS previous_tags
            FROM selected s
        )
        SELECT TO_CHAR(sampled_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'),
               title, category_id, category_name, language, tags, is_mature
        FROM states
        WHERE rn = 1
           OR title IS DISTINCT FROM previous_title
           OR category_id IS DISTINCT FROM previous_category_id
           OR language IS DISTINCT FROM previous_language
           OR tags IS DISTINCT FROM previous_tags
        ORDER BY sampled_at, id
        """,
        (stream_id,),
    )
    return cursor.fetchall()
