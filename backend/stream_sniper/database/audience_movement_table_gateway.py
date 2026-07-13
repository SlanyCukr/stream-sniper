"""Windowed audience-participation movement over stream chatter rollups."""

from .decorators import with_cursor

_AUDIENCE_CTES = """
    WITH current_audience AS (
        SELECT DISTINCT scs.chatter_id
        FROM stream_chatter_stats scs
        JOIN stream s ON s.id = scs.stream_id
        JOIN chatter ch ON ch.id = scs.chatter_id
        WHERE s.creator_id = %(creator_id)s
          AND s.start >= (now() AT TIME ZONE 'UTC') - (%(days)s * interval '1 day')
          AND ch.is_bot IS NOT TRUE
    ), previous_audience AS (
        SELECT DISTINCT scs.chatter_id
        FROM stream_chatter_stats scs
        JOIN stream s ON s.id = scs.stream_id
        JOIN chatter ch ON ch.id = scs.chatter_id
        WHERE s.creator_id = %(creator_id)s
          AND s.start >= (now() AT TIME ZONE 'UTC') - (%(days)s * 2 * interval '1 day')
          AND s.start < (now() AT TIME ZONE 'UTC') - (%(days)s * interval '1 day')
          AND ch.is_bot IS NOT TRUE
    )
"""


@with_cursor
def select_creator_audience_movement_db(creator_id: int, days: int, limit: int, cursor):
    params = {"creator_id": creator_id, "days": days, "limit": limit}
    cursor.execute(
        _AUDIENCE_CTES
        + """
        SELECT
            (SELECT count(*) FROM current_audience),
            (SELECT count(*) FROM previous_audience),
            (SELECT count(*) FROM current_audience c JOIN previous_audience p USING (chatter_id)),
            (SELECT count(*) FROM current_audience c
             LEFT JOIN previous_audience p USING (chatter_id) WHERE p.chatter_id IS NULL),
            (SELECT count(*) FROM previous_audience p
             LEFT JOIN current_audience c USING (chatter_id) WHERE c.chatter_id IS NULL)
        """,
        params,
    )
    summary = cursor.fetchone()

    # "Sources" are other channels where this period's gained chatters participated
    # during the previous period. A chatter may contribute to multiple channels; this is
    # association, deliberately not a causal migration claim.
    cursor.execute(
        _AUDIENCE_CTES
        + """
        , gained AS (
            SELECT c.chatter_id FROM current_audience c
            LEFT JOIN previous_audience p USING (chatter_id)
            WHERE p.chatter_id IS NULL
        )
        SELECT s.creator_id, cr.nick, cr.display_name, count(DISTINCT g.chatter_id)::int
        FROM gained g
        JOIN stream_chatter_stats scs ON scs.chatter_id = g.chatter_id
        JOIN stream s ON s.id = scs.stream_id
        JOIN creator cr ON cr.id = s.creator_id
        WHERE s.creator_id <> %(creator_id)s
          AND s.start >= (now() AT TIME ZONE 'UTC') - (%(days)s * 2 * interval '1 day')
          AND s.start < (now() AT TIME ZONE 'UTC') - (%(days)s * interval '1 day')
        GROUP BY s.creator_id, cr.nick, cr.display_name
        ORDER BY count(DISTINCT g.chatter_id) DESC, s.creator_id
        LIMIT %(limit)s
        """,
        params,
    )
    sources = cursor.fetchall()

    cursor.execute(
        _AUDIENCE_CTES
        + """
        , lapsed AS (
            SELECT p.chatter_id FROM previous_audience p
            LEFT JOIN current_audience c USING (chatter_id)
            WHERE c.chatter_id IS NULL
        )
        SELECT s.creator_id, cr.nick, cr.display_name, count(DISTINCT l.chatter_id)::int
        FROM lapsed l
        JOIN stream_chatter_stats scs ON scs.chatter_id = l.chatter_id
        JOIN stream s ON s.id = scs.stream_id
        JOIN creator cr ON cr.id = s.creator_id
        WHERE s.creator_id <> %(creator_id)s
          AND s.start >= (now() AT TIME ZONE 'UTC') - (%(days)s * interval '1 day')
        GROUP BY s.creator_id, cr.nick, cr.display_name
        ORDER BY count(DISTINCT l.chatter_id) DESC, s.creator_id
        LIMIT %(limit)s
        """,
        params,
    )
    destinations = cursor.fetchall()
    return summary, sources, destinations
