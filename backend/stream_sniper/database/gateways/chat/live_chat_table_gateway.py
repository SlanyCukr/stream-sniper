"""Persistence primitives for real-time Twitch chat capture."""

from collections.abc import Sequence
from datetime import datetime
from typing import NamedTuple

from psycopg2.extensions import connection as Connection
from psycopg2.extensions import cursor as Cursor

from ...core.connection_pool import get_active_pool
from ...core.decorators import with_cursor, with_cursor_connection

LiveMessageRow = tuple[int, int | None, int, int, datetime, bool, str | None, int, str]


@with_cursor_connection
def ensure_live_stream_db(
    cursor: Cursor,
    connection: Connection,
    creator_nick: str,
    twitch_stream_session_id: int,
    started_at: datetime,
    title: str,
    thumbnail_url: str,
) -> int | None:
    """Create or return the provisional stream row for a Twitch live session."""
    cursor.execute(
        """
        WITH creator_row AS (
            SELECT id FROM stream_sniper.creator WHERE lower(nick) = lower(%s)
        ), inserted AS (
            INSERT INTO stream_sniper.stream
                (twitch_id, twitch_stream_session_id, start, creator_id, title,
                 "end", thumbnail_url)
            SELECT -(%s::bigint), %s, %s, id, left(%s, 255), NULL, left(%s, 255)
            FROM creator_row
            ON CONFLICT DO NOTHING
            RETURNING id
        )
        SELECT id FROM inserted
        UNION ALL
        SELECT id FROM stream_sniper.stream WHERE twitch_stream_session_id = %s
        LIMIT 1
        """,
        (
            creator_nick,
            twitch_stream_session_id,
            twitch_stream_session_id,
            started_at,
            title,
            thumbnail_url,
            twitch_stream_session_id,
        ),
    )
    row = cursor.fetchone()
    connection.commit()
    return int(row[0]) if row else None


def insert_live_messages_db(items: Sequence[LiveMessageRow], cursor: Cursor, connection: Connection) -> None:
    """Bulk-insert IRC messages, idempotently keyed by Twitch message UUID."""
    cursor.executemany(
        """
        INSERT INTO stream_sniper.message
            (chatter_id, tagged_chatter_id, stream_id, message_text_id, time,
             is_subscriber, badges, emote_count, source_message_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (source_message_id) WHERE source_message_id IS NOT NULL DO NOTHING
        """,
        items,
    )
    connection.commit()


def bulk_insert_live_messages_db(items: Sequence[LiveMessageRow]) -> None:
    """Write one detached async-sink batch through the shared connection pool."""
    if not items:
        return
    with get_active_pool().get_connection() as connection:
        cursor = connection.cursor()
        try:
            insert_live_messages_db(items, cursor, connection)
        finally:
            cursor.close()


@with_cursor_connection
def finalize_live_stream_db(
    cursor: Cursor,
    connection: Connection,
    stream_id: int,
    ended_at: datetime | None,
) -> None:
    cursor.execute(
        """
        UPDATE stream_sniper.stream s
        SET "end" = COALESCE(%s, now() AT TIME ZONE 'UTC'),
            live_capture_complete = true,
            message_count = (SELECT count(*) FROM stream_sniper.message m WHERE m.stream_id = s.id)
        WHERE s.id = %s
        """,
        (ended_at, stream_id),
    )
    connection.commit()


@with_cursor_connection
def refresh_live_stream_message_counts_db(cursor: Cursor, connection: Connection) -> int:
    """Sync ``stream.message_count`` with reality for every open live-captured stream.

    Only finalize paths ever wrote the counter, so live streams read as 0 messages for
    their whole duration — every consumer (stream catalog, filters, report surfaces)
    showed wrong data exactly while people were watching. Counting from the ``message``
    table (rather than incrementing per flush) also self-corrects any drift from
    deduplicated inserts. Returns the number of streams refreshed.
    """
    cursor.execute(
        """
        UPDATE stream_sniper.stream s
        SET message_count = (SELECT count(*) FROM stream_sniper.message m WHERE m.stream_id = s.id)
        WHERE s."end" IS NULL AND s.twitch_stream_session_id IS NOT NULL
        """
    )
    refreshed = cursor.rowcount
    connection.commit()
    return refreshed


class StaleLiveSessionRow(NamedTuple):
    """One open live-captured stream row with no recent sign of life (sweep candidate)."""

    stream_id: int
    twitch_stream_session_id: int
    creator_nick: str


@with_cursor
def select_stale_live_sessions_db(
    cursor: Cursor,
    stale_after_hours: int,
) -> list[StaleLiveSessionRow]:
    """Return open live-captured rows whose session shows no sign of life (sweep candidates).

    The reconcile loop only finalizes channels in the sink's in-memory map, so a restart
    mid-capture leaks the row as a permanent zombie (``"end"`` stuck NULL,
    ``live_capture_complete`` false — which also blocks VOD reconciliation). A candidate is
    an open live-captured row with no chat message AND no viewer sample for the same Twitch
    session for ``stale_after_hours`` (the sample guard keeps a genuinely-live-but-silent
    tracked stream out of the list). Read-only: the collector confirms each candidate's
    session is really dead (sink state + a live Twitch lookup, failing closed) before
    finalizing it with ``finalize_stale_live_session_db``.
    """
    cursor.execute(
        """
        SELECT s.id, s.twitch_stream_session_id, c.nick
        FROM stream_sniper.stream s
        JOIN stream_sniper.creator c ON c.id = s.creator_id
        WHERE s."end" IS NULL
          AND s.twitch_stream_session_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM stream_sniper.message m
              WHERE m.stream_id = s.id
                AND m.time >= (now() AT TIME ZONE 'UTC') - (%(stale)s * interval '1 hour')
          )
          AND NOT EXISTS (
              SELECT 1 FROM stream_sniper.stream_viewer_sample svs
              WHERE svs.twitch_stream_session_id = s.twitch_stream_session_id
                AND svs.sampled_at >= now() - (%(stale)s * interval '1 hour')
          )
        """,
        {"stale": stale_after_hours},
    )
    return [StaleLiveSessionRow(int(row[0]), int(row[1]), row[2]) for row in cursor.fetchall()]


@with_cursor_connection
def finalize_stale_live_session_db(
    cursor: Cursor,
    connection: Connection,
    stream_id: int,
) -> bool:
    """Finalize one confirmed-dead zombie row; returns False if it was already closed.

    ``"end"`` is set to the last message time — a PROVISIONAL estimate (capture stopped at
    service shutdown, possibly before the stream ended; stream start when no messages
    exist). ``reconcile_live_stream_vod_db`` later repairs it from the VOD's authoritative
    metadata. ``live_capture_complete`` flips true so that VOD reconciliation can happen at
    all. The ``"end" IS NULL`` guard makes the call race-safe against a concurrent real
    finalize.
    """
    cursor.execute(
        """
        UPDATE stream_sniper.stream s
        SET "end" = COALESCE(
                (SELECT max(m.time) FROM stream_sniper.message m WHERE m.stream_id = s.id),
                s.start),
            live_capture_complete = true,
            message_count = (SELECT count(*) FROM stream_sniper.message m WHERE m.stream_id = s.id)
        WHERE s.id = %s AND s."end" IS NULL
        RETURNING s.id
        """,
        (stream_id,),
    )
    finalized = cursor.fetchone() is not None
    connection.commit()
    return finalized


@with_cursor
def select_live_stream_by_session_db(
    cursor: Cursor,
    twitch_stream_session_id: int,
) -> tuple[int, bool] | None:
    cursor.execute(
        """SELECT id, live_capture_complete
           FROM stream_sniper.stream WHERE twitch_stream_session_id = %s""",
        (twitch_stream_session_id,),
    )
    return cursor.fetchone()


# A VOD end only repairs the recorded end when it extends it by more than this. Normal
# live-finalized ends differ from VOD metadata by trailing seconds; repairing those would
# flag every stream's rollup stale for no analytical gain. Swept zombies are off by hours.
_END_REPAIR_MIN_SECONDS = 300


@with_cursor_connection
def reconcile_live_stream_vod_db(
    cursor: Cursor,
    connection: Connection,
    twitch_stream_session_id: int,
    twitch_vod_id: int,
    thumbnail_url: str | None,
    vod_ended_at: datetime | None = None,
) -> tuple[int, bool] | None:
    """Attach the later VOD id to its live row and repair a provisional ``"end"``.

    ``vod_ended_at`` (VOD created_at + duration) is the authoritative session end. It only
    ever EXTENDS the recorded end, and only when the gap exceeds ``_END_REPAIR_MIN_SECONDS``
    (a swept zombie's provisional last-message estimate is hours short; a normal live
    finalize is seconds off and left alone).

    Returns ``(stream_id, rollup_stale)`` — or ``None`` when no completed live capture
    exists for the session. ``rollup_stale`` is DURABLE, not an end-moved flag: it is true
    whenever ``stream_metrics`` is missing or its ``duration_seconds`` disagrees with the
    (post-repair) ``"end" - start`` — mirroring the rollup's own formula — so a rollup
    recompute that fails transiently is retried on every later VOD rediscovery until one
    succeeds, instead of being lost to a one-shot end-changed signal.
    """
    cursor.execute(
        """
        UPDATE stream_sniper.stream s
        SET twitch_id = %(vod_id)s,
            thumbnail_url = COALESCE(%(thumb)s, thumbnail_url),
            "end" = CASE
                WHEN %(vod_end)s::timestamp > s."end" + (%(min_gap)s * interval '1 second')
                THEN %(vod_end)s::timestamp
                ELSE s."end"
            END
        WHERE s.twitch_stream_session_id = %(session_id)s AND s.live_capture_complete
        RETURNING s.id,
            NOT EXISTS (
                SELECT 1 FROM stream_sniper.stream_metrics sm
                WHERE sm.stream_id = s.id
                  AND sm.duration_seconds IS NOT DISTINCT FROM
                      GREATEST(EXTRACT(EPOCH FROM (s."end" - s.start))::int, 0)
            )
        """,
        {
            "vod_id": twitch_vod_id,
            "thumb": thumbnail_url,
            "vod_end": vod_ended_at,
            "min_gap": _END_REPAIR_MIN_SECONDS,
            "session_id": twitch_stream_session_id,
        },
    )
    row = cursor.fetchone()
    connection.commit()
    return (int(row[0]), bool(row[1])) if row else None
