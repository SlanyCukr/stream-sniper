"""
Database gateway for the stream_viewer_sample table (periodic live-viewer snapshots).

The tracking service's stream monitor records one snapshot per tracked streamer on
every poll where the stream is live. Writes must never disrupt the monitoring loop's
state-transition logic, so this module follows the tracking never-raise convention
(mirrors tracking_heartbeat_table_gateway.py): internal try/except, bool/list return,
errors logged and swallowed rather than propagated.
"""

from typing import List, Optional, Tuple

from ..logging_config import get_logger
from .connection_pool import get_pool
from .decorators import log_database_operation, with_cursor

logger = get_logger(__name__)


@log_database_operation
def insert_stream_viewer_sample_db(
    tracked_streamer_id,
    twitch_stream_session_id,
    sampled_at,
    viewer_count,
    title,
    session_started_at,
) -> bool:
    """Insert one viewer snapshot. Duplicate (streamer, session, sampled_at) is a no-op."""
    pool = get_pool()

    try:
        with pool.get_cursor(commit=True) as cursor:
            cursor.execute(
                """
                INSERT INTO stream_sniper.stream_viewer_sample
                    (tracked_streamer_id, twitch_stream_session_id, sampled_at,
                     viewer_count, title, session_started_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (tracked_streamer_id, twitch_stream_session_id, sampled_at)
                DO NOTHING
                """,
                (
                    tracked_streamer_id,
                    twitch_stream_session_id,
                    sampled_at,
                    viewer_count,
                    title,
                    session_started_at,
                ),
            )
            return True
    except Exception as e:
        logger.error(
            f"Error inserting viewer sample for tracked_streamer_id={tracked_streamer_id}, "
            f"session={twitch_stream_session_id}: {e}"
        )
        return False


@log_database_operation
def select_session_viewer_samples_db(
    tracked_streamer_id, twitch_stream_session_id
) -> Optional[List[Tuple]]:
    """Return (sampled_at, viewer_count, title) rows for a session, oldest first, or None on error."""
    pool = get_pool()

    try:
        with pool.get_cursor() as cursor:
            cursor.execute(
                """
                SELECT sampled_at, viewer_count, title
                FROM stream_sniper.stream_viewer_sample
                WHERE tracked_streamer_id = %s AND twitch_stream_session_id = %s
                ORDER BY sampled_at ASC
                """,
                (tracked_streamer_id, twitch_stream_session_id),
            )
            return cursor.fetchall()
    except Exception as e:
        logger.error(
            f"Error selecting viewer samples for tracked_streamer_id={tracked_streamer_id}, "
            f"session={twitch_stream_session_id}: {e}"
        )
        return None


@with_cursor
def select_live_now_db(cursor) -> List[Tuple]:
    """Latest sample per tracked streamer within the last 10 minutes (i.e. currently live).

    Liveness is inferred purely from sample freshness (samples are only written while live,
    on a ~5 min cadence, so 10 min = 2 intervals). Returns one row per streamer:
      (creator_id, nick, display_name, profile_image_url, viewer_count, title,
       session_started_at_iso, sampled_at_iso)
    Timestamps come out UTC-naive ISO strings. Caller sorts by viewer_count DESC.
    """
    cursor.execute(
        """
        SELECT DISTINCT ON (svs.tracked_streamer_id)
               ts.creator_id, c.nick, c.display_name, c.profile_image_url,
               svs.viewer_count, svs.title,
               TO_CHAR(svs.session_started_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'),
               TO_CHAR(svs.sampled_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS')
        FROM stream_viewer_sample svs
        JOIN tracked_streamers ts ON ts.id = svs.tracked_streamer_id
        JOIN creator c ON c.id = ts.creator_id
        WHERE svs.sampled_at >= now() - interval '10 minutes'
        ORDER BY svs.tracked_streamer_id, svs.sampled_at DESC
        """
    )
    return cursor.fetchall()


@with_cursor
def select_latest_sample_time_db(cursor) -> Optional[str]:
    """Newest sampled_at across all viewer samples as a UTC-naive ISO string, or None.

    Surfaces tracker health: a stale value means the tracking container is down, so the UI
    can distinguish "nobody live" from "tracking data is stale".
    """
    cursor.execute(
        """
        SELECT TO_CHAR(MAX(sampled_at) AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS')
        FROM stream_viewer_sample
        """
    )
    row = cursor.fetchone()
    return row[0] if row else None


@with_cursor
def select_stream_viewer_samples_db(stream_id, cursor) -> List[Tuple]:
    """Return viewer-count samples for a stream as (sampled_at_iso, viewer_count), oldest first.

    Samples carry no stream/VOD id (twitch_stream_session_id is a Helix live-session id, a
    different id space than stream.twitch_id), so linkage is creator-level via
    tracked_streamers.creator_id plus a time anchor. The candidate window is always
    [s.start - 10min, COALESCE(s."end", s.start + 12h) + 30min]; sample columns are
    timestamptz while stream.start/"end" are naive UTC, so samples are compared as
    ``sampled_at AT TIME ZONE 'UTC'``. When a live session's session_started_at lands within
    ±15 min of s.start the closest such session wins (and its samples are still clamped to the
    window so a multi-VOD session can't paint the full curve on every VOD page); otherwise all
    windowed samples are returned. Timestamps come out UTC-naive to match the bucket grid.
    """
    cursor.execute(
        """
        WITH tgt AS (
            SELECT s.creator_id AS creator_id,
                   s.start AS s_start,
                   s.start - interval '10 minutes' AS win_start,
                   COALESCE(s."end", s.start + interval '12 hours')
                       + interval '30 minutes' AS win_end
            FROM stream s
            WHERE s.id = %s
        ),
        windowed AS (
            SELECT svs.twitch_stream_session_id AS session_id,
                   svs.session_started_at AS session_started_at,
                   svs.sampled_at AS sampled_at,
                   svs.viewer_count AS viewer_count
            FROM stream_viewer_sample svs
            JOIN tracked_streamers ts ON ts.id = svs.tracked_streamer_id
            JOIN tgt t ON ts.creator_id = t.creator_id
            WHERE svs.sampled_at AT TIME ZONE 'UTC' >= t.win_start
              AND svs.sampled_at AT TIME ZONE 'UTC' <= t.win_end
        ),
        best_session AS (
            SELECT w.session_id
            FROM windowed w
            CROSS JOIN tgt t
            WHERE w.session_started_at IS NOT NULL
              AND abs(EXTRACT(EPOCH FROM
                    (w.session_started_at AT TIME ZONE 'UTC' - t.s_start))) <= 900
            GROUP BY w.session_id
            ORDER BY min(abs(EXTRACT(EPOCH FROM
                    (w.session_started_at AT TIME ZONE 'UTC' - t.s_start))))
            LIMIT 1
        )
        SELECT TO_CHAR(w.sampled_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS'),
               w.viewer_count
        FROM windowed w
        WHERE NOT EXISTS (SELECT 1 FROM best_session)
           OR w.session_id = (SELECT session_id FROM best_session)
        ORDER BY w.sampled_at ASC
        """,
        (stream_id,),
    )
    return cursor.fetchall()
