"""Database gateway for the Creator Wrapped period recap's creator-scoped aggregates.

Mirrors the shape of ``content/scene_wrapped_gateway.py`` and
``creators/scene_chatter_rankings_gateway.py`` but restricted to one creator's streams
instead of the whole scene. Top moments and top copypastas are NOT duplicated here —
``select_scene_highlights_db`` and ``select_scene_copypastas_db`` already accept an
optional ``creator_id`` filter, so the application query reuses them directly.

* ``select_creator_wrapped_totals_db`` — one creator's streams/hours/messages over the
  window (a single aggregate row; an empty window naturally yields
  ``streams=0``/``messages=0`` and ``hours_streamed=None``, since ``SUM`` over zero rows
  is NULL — nullable = unknown, never coalesced to 0).
* ``select_creator_wrapped_chatters_db`` — that creator's top chatters by messages over
  the window (a page, with a ``has_more`` sentinel like the scene ranking gateway).

Active-chatter counts and top emotes come from ``content/scene_wrapped_gateway.py``'s
``select_scene_active_chatters_db``/``select_scene_emotes_db`` via their optional
``creator_id`` filter — no creator-scoped duplicates here.
"""

from typing import NamedTuple

from psycopg2.extensions import cursor as Cursor

from ...core.decorators import with_cursor


class CreatorWrappedTotalsRow(NamedTuple):
    """One creator's stream/hour/message aggregate over the recap window."""

    streams: int
    hours_streamed: float | None
    messages: int


class CreatorWrappedChatterRow(NamedTuple):
    """One ranked chatter within a single creator's window, from ``stream_chatter_stats``."""

    chatter_id: int
    nick: str
    total_messages: int
    streams_attended: int


@with_cursor
def select_creator_wrapped_totals_db(
    cursor: Cursor,
    creator_id: int,
    days: int,
) -> CreatorWrappedTotalsRow:
    """Streams/hours/messages for one creator over the trailing ``days`` window.

    Aggregates ``stream`` directly (no GROUP BY — always exactly one row). An unclosed
    stream contributes 0h via a per-row CASE, matching the scene leaderboard's
    convention; a creator with zero streams in the window yields ``streams=0``,
    ``messages=0``, and ``hours_streamed=None`` (SUM over zero rows is NULL).
    """
    cursor.execute(
        """
        SELECT
            COUNT(*)::int AS streams,
            SUM(CASE WHEN s."end" IS NOT NULL
                     THEN EXTRACT(EPOCH FROM (s."end" - s.start)) ELSE 0 END) / 3600.0 AS hours_streamed,
            COALESCE(SUM(s.message_count), 0)::bigint AS messages
        FROM stream s
        WHERE s.creator_id = %s
          AND s.start >= (now() AT TIME ZONE 'UTC') - (%s * interval '1 day')
        """,
        (creator_id, days),
    )
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("creator wrapped totals returned no row")
    return CreatorWrappedTotalsRow(*row)


@with_cursor
def select_creator_wrapped_chatters_db(
    cursor: Cursor,
    creator_id: int,
    days: int,
    limit: int,
    offset: int,
) -> tuple[list[CreatorWrappedChatterRow], bool]:
    """A page of one creator's top chatters by messages over the trailing window.

    Bots are excluded. Fetches ``limit + 1`` rows; the caller receives the first
    ``limit`` and a boolean overflow flag, matching ``select_scene_chatter_rankings_db``.
    """
    cursor.execute(
        """
        SELECT
            scs.chatter_id,
            c.nick,
            SUM(scs.message_count)::bigint AS total_messages,
            COUNT(DISTINCT scs.stream_id)::int AS streams_attended
        FROM stream_chatter_stats scs
        JOIN stream s ON s.id = scs.stream_id
        JOIN chatter c ON c.id = scs.chatter_id
        WHERE s.creator_id = %s
          AND c.is_bot IS NOT TRUE
          AND s.start >= (now() AT TIME ZONE 'UTC') - (%s * interval '1 day')
        GROUP BY scs.chatter_id, c.nick
        ORDER BY total_messages DESC, scs.chatter_id ASC
        LIMIT %s OFFSET %s
        """,
        (creator_id, days, limit + 1, offset),
    )
    rows = [CreatorWrappedChatterRow(*row) for row in cursor.fetchall()]
    has_more = len(rows) > limit
    return rows[:limit], has_more
