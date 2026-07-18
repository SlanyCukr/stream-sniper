"""Scene-wide trending (velocity) aggregates for copypastas and emotes.

Velocity compares a CURRENT window ``[now-window, now)`` against the PRIOR window
``[now-2*window, now-window)``, both keyed on ``stream.start`` using
``now() AT TIME ZONE 'UTC'``. For each entity the current and prior sums are computed
in a single grouped pass via ``FILTER (WHERE ...)`` aggregate expressions over the
small per-stream rollup tables (``stream_copypasta_stats`` / ``stream_emote_stats``) —
the raw ``message`` table is never scanned on demand. A min-usage floor
(``current_usage >= 5``) drops noise; results are ordered by ``current_usage`` DESC.

Trend classification and delta_pct are derived from these current/prior sums by the
HTTP response models, not here.
"""

from typing import NamedTuple

from psycopg2.extensions import cursor as Cursor

from ...core.decorators import with_cursor
from ...core.wire_format import to_char_wire


class TrendingCopypastaRow(NamedTuple):
    """One copypasta's velocity across the current/prior windows.

    ``first_seen`` is the earliest send time observed in the CURRENT window (ISO 8601),
    or ``None`` when the rollup has no first_seen for those occurrences.
    """

    message_text_id: int
    text: str
    current_usage: int
    prior_usage: int
    stream_count: int
    creator_count: int
    first_seen: str | None


class TrendingEmoteRow(NamedTuple):
    """One emote's velocity across the current/prior windows.

    ``chatter_reach`` SUMs per-stream chatter_count over the CURRENT window;
    ``first_seen`` is the dictionary's global first_seen (ISO 8601), independent of window.
    """

    emote_id: int
    name: str
    source: str
    provider_id: str | None
    current_usage: int
    prior_usage: int
    chatter_reach: int
    first_seen: str | None


# Both windows share these bounds, computed once per statement from the DB clock so the
# current/prior split is consistent even if a boundary is crossed mid-query.
_BOUNDS_CTE = """
    WITH bounds AS (
        SELECT (now() AT TIME ZONE 'UTC')                                    AS cur_end,
               (now() AT TIME ZONE 'UTC') - (%(window)s * interval '1 day')  AS cur_start,
               (now() AT TIME ZONE 'UTC') - (2 * %(window)s * interval '1 day') AS prior_start
    )
"""

# Current-window usage must clear this floor for an entity to appear (cuts single-spike noise).
_MIN_CURRENT_USAGE = 5


@with_cursor
def select_trending_copypastas_db(
    cursor: Cursor,
    window: int,
    creator_id: int | None,
    limit: int,
) -> list[TrendingCopypastaRow]:
    """Rising/falling/new copypastas scene-wide over the current vs prior window.

    Aggregates ``stream_copypasta_stats`` grouped by (message_text_id, text). Current and
    prior usage are separate FILTER'd SUMs in one pass; stream/creator counts and first_seen
    are scoped to the current window. Optional ``creator_id`` restricts both windows.
    """
    params: dict[str, object] = {"window": window, "limit": limit, "floor": _MIN_CURRENT_USAGE}
    creator_clause = ""
    if creator_id is not None:
        creator_clause = "AND s.creator_id = %(creator_id)s"
        params["creator_id"] = creator_id

    cursor.execute(
        f"""
        {_BOUNDS_CTE}
        SELECT scs.message_text_id, mt.text,
               COALESCE(SUM(scs.usage_count)
                   FILTER (WHERE s.start >= b.cur_start AND s.start < b.cur_end), 0) AS current_usage,
               COALESCE(SUM(scs.usage_count)
                   FILTER (WHERE s.start >= b.prior_start AND s.start < b.cur_start), 0) AS prior_usage,
               COUNT(DISTINCT scs.stream_id)
                   FILTER (WHERE s.start >= b.cur_start AND s.start < b.cur_end) AS stream_count,
               COUNT(DISTINCT s.creator_id)
                   FILTER (WHERE s.start >= b.cur_start AND s.start < b.cur_end) AS creator_count,
               {to_char_wire("MIN(scs.first_seen) FILTER (WHERE s.start >= b.cur_start AND s.start < b.cur_end)")}
                   AS first_seen
        FROM stream_copypasta_stats scs
        JOIN stream s ON s.id = scs.stream_id
        JOIN message_text mt ON mt.id = scs.message_text_id
        CROSS JOIN bounds b
        WHERE s.start >= b.prior_start AND s.start < b.cur_end
          {creator_clause}
        GROUP BY scs.message_text_id, mt.text
        HAVING COALESCE(SUM(scs.usage_count)
                   FILTER (WHERE s.start >= b.cur_start AND s.start < b.cur_end), 0) >= %(floor)s
        ORDER BY current_usage DESC, scs.message_text_id ASC
        LIMIT %(limit)s
        """,
        params,
    )
    return [TrendingCopypastaRow(*row) for row in cursor.fetchall()]


@with_cursor
def select_trending_emotes_db(
    cursor: Cursor,
    window: int,
    creator_id: int | None,
    limit: int,
) -> list[TrendingEmoteRow]:
    """Rising/falling/new emotes scene-wide over the current vs prior window.

    Aggregates ``stream_emote_stats`` joined to ``emote_dictionary`` grouped by the emote.
    Current and prior usage are separate FILTER'd SUMs in one pass; chatter_reach SUMs
    per-stream chatter_count over the current window. Optional ``creator_id`` restricts both
    windows. first_seen is the dictionary's global first_seen (window-independent).
    """
    params: dict[str, object] = {"window": window, "limit": limit, "floor": _MIN_CURRENT_USAGE}
    creator_clause = ""
    if creator_id is not None:
        creator_clause = "AND s.creator_id = %(creator_id)s"
        params["creator_id"] = creator_id

    cursor.execute(
        f"""
        {_BOUNDS_CTE}
        SELECT d.id, d.name, d.source, d.provider_id,
               COALESCE(SUM(ses.usage_count)
                   FILTER (WHERE s.start >= b.cur_start AND s.start < b.cur_end), 0) AS current_usage,
               COALESCE(SUM(ses.usage_count)
                   FILTER (WHERE s.start >= b.prior_start AND s.start < b.cur_start), 0) AS prior_usage,
               COALESCE(SUM(ses.chatter_count)
                   FILTER (WHERE s.start >= b.cur_start AND s.start < b.cur_end), 0) AS chatter_reach,
               {to_char_wire("d.first_seen AT TIME ZONE 'UTC'")} AS first_seen
        FROM stream_emote_stats ses
        JOIN stream s ON s.id = ses.stream_id
        JOIN emote_dictionary d ON d.id = ses.emote_id
        CROSS JOIN bounds b
        WHERE s.start >= b.prior_start AND s.start < b.cur_end
          {creator_clause}
        GROUP BY d.id, d.name, d.source, d.provider_id, d.first_seen
        HAVING COALESCE(SUM(ses.usage_count)
                   FILTER (WHERE s.start >= b.cur_start AND s.start < b.cur_end), 0) >= %(floor)s
        ORDER BY current_usage DESC, d.id ASC
        LIMIT %(limit)s
        """,
        params,
    )
    return [TrendingEmoteRow(*row) for row in cursor.fetchall()]
