"""Persistence primitives for real-time Twitch chat capture."""

from collections.abc import Sequence
from datetime import datetime

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
def sweep_stale_live_sessions_db(
    cursor: Cursor,
    connection: Connection,
    stale_after_hours: int,
) -> list[int]:
    """Finalize live-captured stream rows whose session died while the service was down.

    The reconcile loop only finalizes channels in the sink's in-memory map, so a restart
    mid-capture leaks the row as a permanent zombie (``"end"`` stuck NULL,
    ``live_capture_complete`` false — which also blocks VOD reconciliation). This sweep
    closes any open live-captured row with no sign of life for ``stale_after_hours``:
    no chat message AND no viewer sample for the same Twitch session (the sample guard
    keeps a genuinely-live-but-silent tracked stream open). ``"end"`` is set to the last
    message time (the best estimate of when capture actually stopped; stream start when
    no messages exist) and ``live_capture_complete`` flips true so the VOD path can
    reconcile. Returns the swept stream ids so the caller can enqueue their rollups.
    """
    cursor.execute(
        """
        UPDATE stream_sniper.stream s
        SET "end" = COALESCE(
                (SELECT max(m.time) FROM stream_sniper.message m WHERE m.stream_id = s.id),
                s.start),
            live_capture_complete = true,
            message_count = (SELECT count(*) FROM stream_sniper.message m WHERE m.stream_id = s.id)
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
        RETURNING s.id
        """,
        {"stale": stale_after_hours},
    )
    swept = [int(row[0]) for row in cursor.fetchall()]
    connection.commit()
    return swept


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


@with_cursor_connection
def reconcile_live_stream_vod_db(
    cursor: Cursor,
    connection: Connection,
    twitch_stream_session_id: int,
    twitch_vod_id: int,
    thumbnail_url: str | None,
) -> int | None:
    """Attach the later VOD id to its live row so Twitch deep-links remain valid."""
    cursor.execute(
        """
        UPDATE stream_sniper.stream
        SET twitch_id = %s, thumbnail_url = COALESCE(%s, thumbnail_url)
        WHERE twitch_stream_session_id = %s AND live_capture_complete
        RETURNING id
        """,
        (twitch_vod_id, thumbnail_url, twitch_stream_session_id),
    )
    row = cursor.fetchone()
    connection.commit()
    return int(row[0]) if row else None
