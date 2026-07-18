"""Database gateway for the live Moment Radar (chat velocity on currently-live streams).

The live collector writes chat into the canonical ``message`` table within ~5s of send and
creates the ``stream`` row on the first live message (``"end" IS NULL``, a non-null unique
``twitch_stream_session_id``). This gateway reads two index-friendly, deliberately simple
result sets and leaves every derived value (median baseline, ratio, spike flag, zero-fill) to
the pure assembly in the endpoint module:

1. ``select_live_chat_velocity_db`` -> the live-stream metadata rows, and
2. the trailing per-minute message/chatter counts for those streams.

The per-minute query filters on ``stream_id IN (...) AND time >= now-16min`` so the
``message(stream_id, time, id)`` index (migration 0004) drives it as per-stream range scans on
``time``. Read-only; parameterized SQL only.
"""

from typing import NamedTuple

from psycopg2.extensions import cursor as Cursor

from ...core.decorators import with_cursor
from ...core.wire_format import to_char_wire

# Trailing minutes of per-minute data fetched. The radar renders 15 completed minutes and
# needs the earliest of them fully covered even when "now" sits near a minute boundary, so we
# reach back one extra minute (the earliest and current minutes come back partial and are
# dropped by the assembly, which keys strictly on the 15 completed display minutes).
_TRAILING_MINUTES = 16

# Safety bound: a live-captured stream whose row never got closed (``"end"`` stuck NULL) would
# otherwise sit on the radar forever. A real live stream started within the last day.
_LIVE_MAX_AGE_HOURS = 24


class LiveStreamRow(NamedTuple):
    """One currently-live stream with its creator context (from the live-capture columns)."""

    stream_id: int
    creator_id: int
    creator_nick: str
    creator_display_name: str
    profile_image_url: str | None
    stream_title: str | None
    started_at: str | None


class MinuteCountRow(NamedTuple):
    """Per-minute message + distinct-chatter counts for one live stream (one completed minute)."""

    stream_id: int
    minute: str
    messages: int
    unique_chatters: int


@with_cursor
def select_live_chat_velocity_db(cursor: Cursor) -> tuple[list[LiveStreamRow], list[MinuteCountRow]]:
    """Return (live-stream metadata, trailing per-minute counts) for currently-live streams.

    A stream is "live" when ``"end" IS NULL`` and it carries a ``twitch_stream_session_id``
    (set only for live-captured streams), started within the last ``_LIVE_MAX_AGE_HOURS`` hours
    (a bound against zombie rows). Per-minute counts cover the trailing ``_TRAILING_MINUTES``
    minutes and are grouped on ``date_trunc('minute', time)``; the caller keeps only the 15
    completed display minutes and excludes the current in-progress minute. Two live streams with
    no chat in the window simply produce no per-minute rows (the assembly zero-fills them).
    """
    cursor.execute(
        f"""
        SELECT
            s.id,
            s.creator_id,
            c.nick,
            c.display_name,
            c.profile_image_url,
            s.title,
            {to_char_wire("s.start")}
        FROM stream s
        JOIN creator c ON c.id = s.creator_id
        WHERE s."end" IS NULL
          AND s.twitch_stream_session_id IS NOT NULL
          AND s.start >= (now() AT TIME ZONE 'UTC') - (%(max_age)s * interval '1 hour')
        """,
        {"max_age": _LIVE_MAX_AGE_HOURS},
    )
    live_rows = [LiveStreamRow(*row) for row in cursor.fetchall()]
    if not live_rows:
        return [], []

    stream_ids = [row.stream_id for row in live_rows]
    cursor.execute(
        f"""
        SELECT
            m.stream_id,
            {to_char_wire("date_trunc('minute', m.time)")},
            COUNT(*),
            COUNT(DISTINCT m.chatter_id)
        FROM message m
        WHERE m.stream_id = ANY(%(stream_ids)s)
          AND m.time >= (now() AT TIME ZONE 'UTC') - (%(trailing)s * interval '1 minute')
        GROUP BY m.stream_id, date_trunc('minute', m.time)
        """,
        {"stream_ids": stream_ids, "trailing": _TRAILING_MINUTES},
    )
    minute_rows = [MinuteCountRow(*row) for row in cursor.fetchall()]
    return live_rows, minute_rows
