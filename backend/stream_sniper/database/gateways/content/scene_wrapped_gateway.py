"""Database gateway for the Scene Wrapped period recap's two bespoke aggregates.

Everything else the recap needs is already served by existing scene gateways
(leaderboard, chatter rankings, highlights, copypastas, events). This module owns the
two remaining data sources, both windowed on ``stream.start`` and both reading only the
small per-stream rollup tables (the raw ``message`` table is never scanned on demand):

* ``select_scene_emotes_db`` — scene-wide emote usage over the window (top by usage).
* ``select_scene_active_chatters_db`` — distinct human chatters over the window.
"""

from typing import NamedTuple

from psycopg2.extensions import cursor as Cursor

from ...core.decorators import with_cursor


class SceneWrappedEmoteRow(NamedTuple):
    """One emote's scene-wide usage over the recap window.

    ``usage`` SUMs per-stream usage_count; ``chatter_reach`` SUMs per-stream chatter_count
    (so it double-counts a chatter who used the emote across several streams — an honest
    "reach" label over per-stream rollups, not a global distinct count).
    """

    emote_id: int
    name: str
    source: str
    usage: int
    chatter_reach: int


@with_cursor
def select_scene_emotes_db(
    cursor: Cursor,
    days: int,
    limit: int,
    *,
    creator_id: int | None = None,
) -> list[SceneWrappedEmoteRow]:
    """Top emotes by usage over the trailing ``days`` window.

    Aggregates ``stream_emote_stats`` joined to its ``stream`` (windowed on ``s.start``)
    and to ``emote_dictionary`` for name/source, grouped by emote and ordered by total
    usage (id tiebreak for a total, stable order). Returns at most ``limit`` rows.
    ``creator_id`` narrows the window to one creator's streams (Creator Wrapped).
    """
    creator_filter = "AND s.creator_id = %s" if creator_id is not None else ""
    params: list[object] = [days] if creator_id is None else [days, creator_id]
    params.append(limit)
    cursor.execute(
        f"""
        SELECT d.id, d.name, d.source,
               SUM(ses.usage_count)::bigint   AS usage,
               SUM(ses.chatter_count)::bigint AS chatter_reach
        FROM stream_emote_stats ses
        JOIN stream s ON s.id = ses.stream_id
        JOIN emote_dictionary d ON d.id = ses.emote_id
        WHERE s.start >= (now() AT TIME ZONE 'UTC') - (%s * interval '1 day')
          {creator_filter}
        GROUP BY d.id, d.name, d.source
        ORDER BY usage DESC, d.id ASC
        LIMIT %s
        """,
        tuple(params),
    )
    return [SceneWrappedEmoteRow(*row) for row in cursor.fetchall()]


@with_cursor
def select_scene_active_chatters_db(
    cursor: Cursor,
    days: int,
    *,
    creator_id: int | None = None,
) -> int:
    """Count of distinct human chatters active over the trailing ``days`` window.

    Counts ``DISTINCT chatter_id`` over ``stream_chatter_stats`` joined to its ``stream``
    (windowed on ``s.start``), excluding bots (``chatter.is_bot IS NOT TRUE`` — an
    unclassified NULL is kept, matching the scene's other bot filters).
    ``creator_id`` narrows the window to one creator's streams (Creator Wrapped).
    """
    creator_filter = "AND s.creator_id = %s" if creator_id is not None else ""
    params: list[object] = [days] if creator_id is None else [days, creator_id]
    cursor.execute(
        f"""
        SELECT COUNT(DISTINCT scs.chatter_id)
        FROM stream_chatter_stats scs
        JOIN stream s ON s.id = scs.stream_id
        JOIN chatter c ON c.id = scs.chatter_id
        WHERE c.is_bot IS NOT TRUE
          AND s.start >= (now() AT TIME ZONE 'UTC') - (%s * interval '1 day')
          {creator_filter}
        """,
        tuple(params),
    )
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("scene active-chatter count returned no row")
    return int(row[0])
