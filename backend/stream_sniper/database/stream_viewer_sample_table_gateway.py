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
from .decorators import log_database_operation

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
