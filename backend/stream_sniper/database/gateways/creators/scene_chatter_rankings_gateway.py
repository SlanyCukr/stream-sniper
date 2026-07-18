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

Archetype badges are identity claims, so every input feeding them is account-wide
regardless of the ranking window: ``first_seen`` (earliest
``creator_chatter_stats.first_seen_at``) and the ``lifetime_*`` fields (messages,
streams, creators, and the top channel's messages, all aggregated over
``creator_chatter_stats``). Only the displayed rank metrics
(``total_messages``/``streams_attended``/``creators_visited``/``home_*``) are
window-scoped. Without this split a lifetime loyalist who spread out for one week
would badge as Wanderer on the 7-day tab — window slices are rankings, not identity.
"""

from typing import NamedTuple

from psycopg2.extensions import cursor as Cursor

from ...core.decorators import with_cursor
from ...core.wire_format import to_char_wire


class SceneChatterRankRow(NamedTuple):
    """One ranked chatter plus their home-channel slice, from the rollup tables.

    ``home_*`` fields are populated from the top creator by messages within the
    same window; they are only ``None`` for the degenerate no-creator case that a
    ``LEFT JOIN LATERAL`` guards against (never happens for a chatter that appears
    in the aggregate at all). ``first_seen`` is the account-wide earliest
    first-seen wire timestamp (``None`` = unknown era).

    The ``lifetime_*`` fields are ALWAYS account-wide (identical to the display
    aggregates on the all-time path; independently aggregated on windowed paths)
    and exist solely to feed archetype computation — identity badges must not
    flip with the ranking window. ``lifetime_home_messages`` is the top channel's
    lifetime message count (``None`` when the chatter has no per-creator rollup).
    """

    chatter_id: int
    nick: str
    total_messages: int
    streams_attended: int
    creators_visited: int
    first_seen: str | None
    home_creator_id: int | None
    home_creator_nick: str | None
    home_creator_display_name: str | None
    home_messages: int | None
    lifetime_messages: int
    lifetime_streams: int
    lifetime_creators: int
    lifetime_home_messages: int | None


# All-time: aggregate the per-creator rollup, then attach each chatter's top creator.
_ALL_TIME_SQL = f"""
    WITH agg AS (
        SELECT
            ccs.chatter_id,
            SUM(ccs.total_messages)::bigint AS total_messages,
            SUM(ccs.streams_attended)::int  AS streams_attended,
            COUNT(DISTINCT ccs.creator_id)::int AS creators_visited,
            MIN(ccs.first_seen_at) AS first_seen_at
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
        {to_char_wire("a.first_seen_at")},
        home.creator_id,
        home.creator_nick,
        home.creator_display_name,
        home.messages,
        a.total_messages    AS lifetime_messages,
        a.streams_attended  AS lifetime_streams,
        a.creators_visited  AS lifetime_creators,
        home.messages       AS lifetime_home_messages
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
# the top creator computed over that same window plus the account-wide identity
# aggregates (first-seen and lifetime totals from creator_chatter_stats, never
# limited to the window — see module docstring). The identity lateral runs only on
# the <= limit+1 page rows, so it adds one indexed aggregate per returned row.
_WINDOWED_SQL = f"""
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
        {to_char_wire("fs.first_seen_at")},
        home.creator_id,
        home.creator_nick,
        home.creator_display_name,
        home.messages,
        COALESCE(fs.lifetime_messages, 0) AS lifetime_messages,
        COALESCE(fs.lifetime_streams, 0)  AS lifetime_streams,
        COALESCE(fs.lifetime_creators, 0) AS lifetime_creators,
        fs.lifetime_home_messages
    FROM agg a
    JOIN stream_sniper.chatter ch ON ch.id = a.chatter_id
    LEFT JOIN LATERAL (
        SELECT
            MIN(ccs.first_seen_at)          AS first_seen_at,
            SUM(ccs.total_messages)::bigint AS lifetime_messages,
            SUM(ccs.streams_attended)::int  AS lifetime_streams,
            COUNT(ccs.creator_id)::int      AS lifetime_creators,
            MAX(ccs.total_messages)::bigint AS lifetime_home_messages
        FROM stream_sniper.creator_chatter_stats ccs
        WHERE ccs.chatter_id = a.chatter_id
    ) fs ON TRUE
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
