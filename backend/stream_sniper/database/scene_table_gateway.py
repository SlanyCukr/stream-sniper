"""Database gateway for the scene-wide leaderboard.

Cheap aggregates over the small `stream` + `stream_metrics` tables (one GROUP BY,
no `message` scan). Peak viewers is a SEPARATE aggregate over stream_viewer_sample
(creator-linked via tracked_streamers) merged in Python by creator_id, so the two
big tables are never cross-joined.
"""

from .decorators import with_cursor


@with_cursor
def select_scene_leaderboard_db(days: int, cursor):
    """Per-creator activity aggregate over the last `days` days.

    Returns rows ordered by total_messages DESC:
      (creator_id, nick, display_name, profile_image_url, streams, hours_streamed,
       total_messages, msgs_per_min, chatter_appearances)

    hours_streamed skips unclosed streams (NULL "end") via a per-row CASE. msgs_per_min
    is NULL when there is no rolled-up duration (SUM = 0), so un-rolled creators surface
    as unknown rather than 0 (nullable = unknown). chatter_appearances SUMs per-stream
    unique_chatters, so it double-counts across streams — an honest "appearances" label.
    """
    cursor.execute(
        """
        SELECT s.creator_id, c.nick, c.display_name, c.profile_image_url,
               COUNT(*) AS streams,
               SUM(CASE WHEN s."end" IS NOT NULL
                        THEN EXTRACT(EPOCH FROM (s."end" - s.start)) ELSE 0 END) / 3600.0 AS hours,
               SUM(s.message_count) AS total_messages,
               SUM(COALESCE(sm.total_messages, 0))::float
                   / NULLIF(SUM(COALESCE(sm.duration_seconds, 0)) / 60.0, 0) AS msgs_per_min,
               SUM(COALESCE(sm.unique_chatters, 0)) AS chatter_appearances
        FROM stream s
        JOIN creator c ON c.id = s.creator_id
        LEFT JOIN stream_metrics sm ON sm.stream_id = s.id
        WHERE s.start >= (now() AT TIME ZONE 'UTC') - (%s * interval '1 day')
        GROUP BY s.creator_id, c.nick, c.display_name, c.profile_image_url
        ORDER BY total_messages DESC, s.creator_id ASC
        """,
        (days,),
    )
    return cursor.fetchall()


@with_cursor
def select_scene_peak_viewers_db(days: int, cursor):
    """Max live viewer_count per creator over the last `days` days.

    Reads stream_viewer_sample via tracked_streamers (no stream join — sample ids live
    in a different id space). Returns (creator_id, peak_viewers) rows; creators with no
    samples in the window are simply absent (the caller leaves peak_viewers None).
    """
    cursor.execute(
        """
        SELECT ts.creator_id, MAX(svs.viewer_count)
        FROM stream_viewer_sample svs
        JOIN tracked_streamers ts ON ts.id = svs.tracked_streamer_id
        WHERE svs.sampled_at >= now() - (%s * interval '1 day')
        GROUP BY ts.creator_id
        """,
        (days,),
    )
    return cursor.fetchall()
