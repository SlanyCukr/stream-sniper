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

# Liveness freshness bound, matching ``select_live_now_db``'s definition of "currently live":
# viewer samples are only written while a stream is live, on a ~5-minute cadence, so a sample
# (or, as a fallback, any chat message) within this window proves the session is still alive.
# This is deliberately NOT a stream-start age bound — a marathon stream stays on the radar for
# as long as it keeps producing samples/chat, while a zombie row (``"end"`` stuck NULL) drops
# off within minutes of the session actually ending instead of lingering for hours.
_LIVENESS_WINDOW_MINUTES = 10


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

    A stream is "live" when ``"end" IS NULL``, it carries a ``twitch_stream_session_id``
    (set only for live-captured streams), and the session shows signs of life within the last
    ``_LIVENESS_WINDOW_MINUTES`` minutes: a viewer sample for the same Twitch session (the
    tracking service samples every live tracked streamer on a ~5-minute cadence — the same
    freshness signal ``select_live_now_db`` uses) or, as a fallback for tracking-service
    downtime, a chat message. Stream-start age is deliberately NOT a criterion: marathon
    streams stay visible indefinitely, while zombie rows (``"end"`` stuck NULL after the
    session died) disappear within minutes. Per-minute counts cover the trailing ``_TRAILING_MINUTES``
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
          AND (
            EXISTS (
                SELECT 1
                FROM stream_viewer_sample svs
                WHERE svs.twitch_stream_session_id = s.twitch_stream_session_id
                  AND svs.sampled_at >= now() - (%(liveness)s * interval '1 minute')
            )
            OR EXISTS (
                SELECT 1
                FROM message m
                WHERE m.stream_id = s.id
                  AND m.time >= (now() AT TIME ZONE 'UTC') - (%(liveness)s * interval '1 minute')
            )
          )
        """,
        {"liveness": _LIVENESS_WINDOW_MINUTES},
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
