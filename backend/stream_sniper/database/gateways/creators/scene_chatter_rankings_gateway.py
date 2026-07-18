"""Scene-wide chatter power-rankings reads (public leaderboard).

Two aggregate paths over the small per-chatter rollup tables (no message scan):

* ``window="all"`` aggregates ``creator_chatter_stats`` across every creator the
  chatter has chatted in.
* ``window=7`` / ``window=30`` aggregates ``stream_chatter_stats`` joined to
  ``stream`` restricted to streams that started inside the trailing window.

Both paths exclude bots (``chatter.is_bot IS NOT TRUE``), rank by total messages
(ties break on the lower chatter id), and resolve a ``home_channel`` — the single
creator the chatter sent the most messages to within the same scope — via a
``LEFT JOIN LATERAL``. Each query fetches ``limit + 1`` rows so the caller can read
a ``has_more`` sentinel off the overflow row.
"""

from typing import NamedTuple

from psycopg2.extensions import cursor as Cursor

from ...core.decorators import with_cursor


class SceneChatterRankRow(NamedTuple):
    """One ranked chatter plus their home-channel slice, from the rollup tables.

    ``home_*`` fields are populated from the top creator by messages within the
    same window; they are only ``None`` for the degenerate no-creator case that a
    ``LEFT JOIN LATERAL`` guards against (never happens for a chatter that appears
    in the aggregate at all).
    """

    chatter_id: int
    nick: str
    total_messages: int
    streams_attended: int
    creators_visited: int
    home_creator_id: int | None
    home_creator_nick: str | None
    home_creator_display_name: str | None
    home_messages: int | None


# All-time: aggregate the per-creator rollup, then attach each chatter's top creator.
_ALL_TIME_SQL = """
    WITH agg AS (
        SELECT
            ccs.chatter_id,
            SUM(ccs.total_messages)::bigint AS total_messages,
            SUM(ccs.streams_attended)::int  AS streams_attended,
            COUNT(DISTINCT ccs.creator_id)::int AS creators_visited
        FROM stream_sniper.creator_chatter_stats ccs
        JOIN stream_sniper.chatter c ON c.id = ccs.chatter_id
        WHERE c.is_bot IS NOT TRUE
        GROUP BY ccs.chatter_id
        ORDER BY total_messages DESC, ccs.chatter_id ASC
        LIMIT %s OFFSET %s
    )
    SELECT
        a.chatter_id,
        ch.nick,
        a.total_messages,
        a.streams_attended,
        a.creators_visited,
        home.creator_id,
        home.creator_nick,
        home.creator_display_name,
        home.messages
    FROM agg a
    JOIN stream_sniper.chatter ch ON ch.id = a.chatter_id
    LEFT JOIN LATERAL (
        SELECT
            ccs2.creator_id,
            cr.nick         AS creator_nick,
            cr.display_name AS creator_display_name,
            ccs2.total_messages::bigint AS messages
        FROM stream_sniper.creator_chatter_stats ccs2
        JOIN stream_sniper.creator cr ON cr.id = ccs2.creator_id
        WHERE ccs2.chatter_id = a.chatter_id
        ORDER BY ccs2.total_messages DESC, ccs2.creator_id ASC
        LIMIT 1
    ) home ON TRUE
    ORDER BY a.total_messages DESC, a.chatter_id ASC
"""

# Windowed: aggregate the per-stream rollup within the trailing window, then attach
# the top creator computed over that same window.
_WINDOWED_SQL = """
    WITH agg AS (
        SELECT
            scs.chatter_id,
            SUM(scs.message_count)::bigint  AS total_messages,
            COUNT(DISTINCT scs.stream_id)::int  AS streams_attended,
            COUNT(DISTINCT s.creator_id)::int   AS creators_visited
        FROM stream_sniper.stream_chatter_stats scs
        JOIN stream_sniper.stream s ON s.id = scs.stream_id
        JOIN stream_sniper.chatter c ON c.id = scs.chatter_id
        WHERE c.is_bot IS NOT TRUE
          AND s.start >= (now() AT TIME ZONE 'UTC') - (%s * interval '1 day')
        GROUP BY scs.chatter_id
        ORDER BY total_messages DESC, scs.chatter_id ASC
        LIMIT %s OFFSET %s
    )
    SELECT
        a.chatter_id,
        ch.nick,
        a.total_messages,
        a.streams_attended,
        a.creators_visited,
        home.creator_id,
        home.creator_nick,
        home.creator_display_name,
        home.messages
    FROM agg a
    JOIN stream_sniper.chatter ch ON ch.id = a.chatter_id
    LEFT JOIN LATERAL (
        SELECT
            s2.creator_id,
            cr.nick         AS creator_nick,
            cr.display_name AS creator_display_name,
            SUM(scs2.message_count)::bigint AS messages
        FROM stream_sniper.stream_chatter_stats scs2
        JOIN stream_sniper.stream s2 ON s2.id = scs2.stream_id
        JOIN stream_sniper.creator cr ON cr.id = s2.creator_id
        WHERE scs2.chatter_id = a.chatter_id
          AND s2.start >= (now() AT TIME ZONE 'UTC') - (%s * interval '1 day')
        GROUP BY s2.creator_id, cr.nick, cr.display_name
        ORDER BY messages DESC, s2.creator_id ASC
        LIMIT 1
    ) home ON TRUE
    ORDER BY a.total_messages DESC, a.chatter_id ASC
"""


@with_cursor
def select_scene_chatter_rankings_db(
    cursor: Cursor,
    window_days: int | None,
    limit: int,
    offset: int,
) -> tuple[list[SceneChatterRankRow], bool]:
    """A page of ranked chatters plus a ``has_more`` sentinel.

    ``window_days`` is ``None`` for the all-time aggregate, or ``7`` / ``30`` for a
    trailing-window aggregate. Bots are excluded in both paths. Fetches ``limit + 1``
    rows; the caller receives the first ``limit`` and a boolean overflow flag.
    """
    if window_days is None:
        cursor.execute(_ALL_TIME_SQL, (limit + 1, offset))
    else:
        cursor.execute(_WINDOWED_SQL, (window_days, limit + 1, offset, window_days))
    rows = [SceneChatterRankRow(*row) for row in cursor.fetchall()]
    has_more = len(rows) > limit
    return rows[:limit], has_more
