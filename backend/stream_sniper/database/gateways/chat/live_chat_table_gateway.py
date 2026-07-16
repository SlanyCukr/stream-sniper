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
