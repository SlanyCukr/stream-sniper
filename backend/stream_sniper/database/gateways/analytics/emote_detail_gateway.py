"""Single-emote drill-down reads over the per-stream emote rollup.

All queries aggregate ``stream_emote_stats`` (joined to ``emote_dictionary`` /
``stream`` / ``creator``) — the raw ``message`` table is never scanned. Lifetime
scope (no window): the detail page answers "what is this emote's story here",
not "is it trending" (that's ``scene_trends_gateway``).
"""

from typing import NamedTuple

from psycopg2.extensions import cursor as Cursor

from ...core.decorators import with_cursor
from ...core.wire_format import to_char_wire


class EmoteMetaRow(NamedTuple):
    """Dictionary identity for one emote; ``first_seen`` is the global dictionary time."""

    emote_id: int
    name: str
    source: str
    provider_id: str | None
    first_seen: str | None


class EmoteTotalsRow(NamedTuple):
    """Lifetime aggregates across every stream the emote appeared in.

    ``chatter_reach`` SUMs per-stream chatter_count (a chatter attending N streams
    counts N times — same contract as the trending endpoint's reach).
    """

    usage: int
    chatter_reach: int
    stream_count: int
    creator_count: int
    last_used: str | None


class EmoteCreatorUsageRow(NamedTuple):
    """One channel's lifetime usage of the emote."""

    creator_id: int
    nick: str
    display_name: str
    usage: int
    chatter_reach: int
    stream_count: int


class EmoteWeeklyUsageRow(NamedTuple):
    """Usage summed per ISO week (``week_start`` = Monday, ISO 8601 date)."""

    week_start: str
    usage: int


class EmoteStreamUsageRow(NamedTuple):
    """One recent stream the emote appeared in."""

    stream_id: int
    title: str | None
    start: str | None
    creator_id: int
    creator_nick: str
    creator_display_name: str
    usage: int
    chatter_count: int


@with_cursor
def select_emote_meta_db(cursor: Cursor, emote_id: int) -> EmoteMetaRow | None:
    """Dictionary identity for one emote, or None when the id is unknown."""
    cursor.execute(
        f"""
        SELECT d.id, d.name, d.source, d.provider_id,
               {to_char_wire("d.first_seen AT TIME ZONE 'UTC'")} AS first_seen
        FROM emote_dictionary d
        WHERE d.id = %s
        """,
        (emote_id,),
    )
    row = cursor.fetchone()
    return EmoteMetaRow(*row) if row else None


@with_cursor
def select_emote_totals_db(cursor: Cursor, emote_id: int) -> EmoteTotalsRow:
    """Lifetime usage totals; all-zero (last_used None) when the emote was never used."""
    cursor.execute(
        f"""
        SELECT COALESCE(SUM(ses.usage_count), 0)::bigint AS usage,
               COALESCE(SUM(ses.chatter_count), 0)::bigint AS chatter_reach,
               COUNT(DISTINCT ses.stream_id)::int AS stream_count,
               COUNT(DISTINCT s.creator_id)::int AS creator_count,
               {to_char_wire("MAX(s.start)")} AS last_used
        FROM stream_emote_stats ses
        JOIN stream s ON s.id = ses.stream_id
        WHERE ses.emote_id = %s
        """,
        (emote_id,),
    )
    row = cursor.fetchone()
    if row is None:  # aggregate always yields one row; guard for the type checker
        return EmoteTotalsRow(usage=0, chatter_reach=0, stream_count=0, creator_count=0, last_used=None)
    return EmoteTotalsRow(*row)


@with_cursor
def select_emote_top_creators_db(cursor: Cursor, emote_id: int, limit: int) -> list[EmoteCreatorUsageRow]:
    """Channels ranked by lifetime usage of the emote."""
    cursor.execute(
        """
        SELECT s.creator_id, c.nick, c.display_name,
               SUM(ses.usage_count)::bigint AS usage,
               SUM(ses.chatter_count)::bigint AS chatter_reach,
               COUNT(DISTINCT ses.stream_id)::int AS stream_count
        FROM stream_emote_stats ses
        JOIN stream s ON s.id = ses.stream_id
        JOIN creator c ON c.id = s.creator_id
        WHERE ses.emote_id = %s
        GROUP BY s.creator_id, c.nick, c.display_name
        ORDER BY usage DESC, c.nick ASC
        LIMIT %s
        """,
        (emote_id, limit),
    )
    return [EmoteCreatorUsageRow(*row) for row in cursor.fetchall()]


@with_cursor
def select_emote_weekly_usage_db(cursor: Cursor, emote_id: int, weeks: int) -> list[EmoteWeeklyUsageRow]:
    """Usage per ISO week over the trailing ``weeks`` weeks, oldest first.

    Weeks with no usage are absent (the chart treats missing weeks as zero);
    bucketing keys on ``stream.start`` like every other scene aggregate.
    """
    cursor.execute(
        """
        SELECT TO_CHAR(DATE_TRUNC('week', s.start), 'YYYY-MM-DD') AS week_start,
               SUM(ses.usage_count)::bigint AS usage
        FROM stream_emote_stats ses
        JOIN stream s ON s.id = ses.stream_id
        WHERE ses.emote_id = %s
          AND s.start >= DATE_TRUNC('week', (now() AT TIME ZONE 'UTC')) - (%s * interval '1 week')
        GROUP BY DATE_TRUNC('week', s.start)
        ORDER BY week_start ASC
        """,
        (emote_id, weeks),
    )
    return [EmoteWeeklyUsageRow(*row) for row in cursor.fetchall()]


@with_cursor
def select_emote_recent_streams_db(cursor: Cursor, emote_id: int, limit: int) -> list[EmoteStreamUsageRow]:
    """Most recent streams the emote appeared in, newest first."""
    cursor.execute(
        f"""
        SELECT s.id, s.title, {to_char_wire("s.start")} AS start,
               s.creator_id, c.nick, c.display_name,
               ses.usage_count, ses.chatter_count
        FROM stream_emote_stats ses
        JOIN stream s ON s.id = ses.stream_id
        JOIN creator c ON c.id = s.creator_id
        WHERE ses.emote_id = %s
        ORDER BY s.start DESC NULLS LAST, s.id DESC
        LIMIT %s
        """,
        (emote_id, limit),
    )
    return [EmoteStreamUsageRow(*row) for row in cursor.fetchall()]
