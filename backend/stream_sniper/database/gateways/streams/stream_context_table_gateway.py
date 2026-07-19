"""Live stream context snapshots and VOD-time-window linkage."""

from psycopg2.extensions import cursor as Cursor

from stream_sniper.database.gateways.streams.records import (
    StreamContextChangeRow,
)

from ...core.decorators import with_cursor
from ...core.wire_format import to_char_wire


@with_cursor
def select_stream_context_changes_db(
    cursor: Cursor,
    stream_id: int,
) -> list[StreamContextChangeRow]:
    """Return only changed context states linked to a stored VOD by creator/time."""
    cursor.execute(
        f"""
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
        SELECT {to_char_wire("sampled_at AT TIME ZONE 'UTC'")},
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
    return [StreamContextChangeRow(*row) for row in cursor.fetchall()]
