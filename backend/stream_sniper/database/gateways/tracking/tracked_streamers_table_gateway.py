"""
Database gateway for tracked_streamers table operations.
"""

from datetime import datetime

from stream_sniper.application.tracking.models import TrackedStreamer
from stream_sniper.database.core.patches import (
    UNSET,
    Unset,
)

from ...core.decorators import read_cursor, write_cursor


def _build_tracked_streamer_filter(
    is_active: bool | None,
    processing_enabled: bool | None,
) -> tuple[str, list[object]]:
    clauses: list[str] = []
    params: list[object] = []
    if is_active is not None:
        clauses.append("ts.is_active = %s")
        params.append(is_active)
    if processing_enabled is not None:
        clauses.append("ts.processing_enabled = %s")
        params.append(processing_enabled)
    return (f"WHERE {' AND '.join(clauses)}" if clauses else "", params)


def insert_tracked_streamer_db(
    creator_id: int,
    twitch_username: str,
    display_name: str,
    created_by: int,
    notes: str | None = None,
    is_active: bool = True,
    processing_enabled: bool = True,
) -> int | None:

    with write_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO stream_sniper.tracked_streamers
            (creator_id, twitch_username, display_name, created_by, notes, is_active, processing_enabled)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (creator_id, twitch_username, display_name, created_by, notes, is_active, processing_enabled),
        )
        result = cursor.fetchone()
        return result[0] if result else None


def select_tracked_streamers_db(
    limit: int = 100, offset: int = 0, is_active: bool | None = None, processing_enabled: bool | None = None
) -> list[TrackedStreamer]:

    with read_cursor() as cursor:
        where_clause, params = _build_tracked_streamer_filter(is_active, processing_enabled)
        params.extend([limit, offset])

        query = f"""
            SELECT ts.id, ts.creator_id, ts.twitch_username, ts.display_name, ts.is_active,
                   ts.last_stream_check, ts.last_processed_vod_id, ts.processing_enabled,
                   ts.created_at, ts.updated_at, ts.created_by, ts.notes,
                   c.display_name as creator_display_name, c.profile_image_url,
                   u.username as created_by_username
            FROM stream_sniper.tracked_streamers ts
            JOIN stream_sniper.creator c ON ts.creator_id = c.id
            LEFT JOIN stream_sniper.users u ON ts.created_by = u.id
            {where_clause}
            ORDER BY ts.created_at DESC
            LIMIT %s OFFSET %s
        """

        cursor.execute(query, params)
        return [TrackedStreamer(*row) for row in cursor.fetchall()]


def select_tracked_streamer_by_id_db(tracked_streamer_id: int) -> TrackedStreamer | None:

    with read_cursor() as cursor:
        cursor.execute(
            """
            SELECT ts.id, ts.creator_id, ts.twitch_username, ts.display_name, ts.is_active,
                   ts.last_stream_check, ts.last_processed_vod_id, ts.processing_enabled,
                   ts.created_at, ts.updated_at, ts.created_by, ts.notes,
                   c.display_name as creator_display_name, c.profile_image_url,
                   u.username as created_by_username
            FROM stream_sniper.tracked_streamers ts
            JOIN stream_sniper.creator c ON ts.creator_id = c.id
            LEFT JOIN stream_sniper.users u ON ts.created_by = u.id
            WHERE ts.id = %s
            """,
            (tracked_streamer_id,),
        )
        row = cursor.fetchone()
        return TrackedStreamer(*row) if row else None


def update_tracked_streamer_db(
    tracked_streamer_id: int,
    *,
    twitch_username: str | Unset = UNSET,
    display_name: str | Unset = UNSET,
    is_active: bool | Unset = UNSET,
    last_stream_check: datetime | None | Unset = UNSET,
    last_processed_twitch_vod_id: int | None | Unset = UNSET,
    processing_enabled: bool | Unset = UNSET,
    notes: str | None | Unset = UNSET,
) -> bool:
    """Update supplied fields; ``UNSET`` distinguishes omission from explicit null."""

    set_clauses: list[str] = []
    params: list[object] = []

    values = {
        "twitch_username": twitch_username,
        "display_name": display_name,
        "is_active": is_active,
        "last_stream_check": last_stream_check,
        "last_processed_vod_id": last_processed_twitch_vod_id,
        "processing_enabled": processing_enabled,
        "notes": notes,
    }
    for field, value in values.items():
        if value is not UNSET:
            set_clauses.append(f"{field} = %s")
            params.append(value)

    if not set_clauses:
        return False

    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    params.append(tracked_streamer_id)

    with write_cursor() as cursor:
        query = f"""
            UPDATE stream_sniper.tracked_streamers
            SET {", ".join(set_clauses)}
            WHERE id = %s
        """
        cursor.execute(query, params)
        return bool(cursor.rowcount > 0)


def delete_tracked_streamer_db(tracked_streamer_id: int) -> bool:

    with write_cursor() as cursor:
        cursor.execute("DELETE FROM stream_sniper.tracked_streamers WHERE id = %s", (tracked_streamer_id,))
        return bool(cursor.rowcount > 0)


def count_tracked_streamers_db(is_active: bool | None = None, processing_enabled: bool | None = None) -> int:

    with read_cursor() as cursor:
        where_clause, params = _build_tracked_streamer_filter(is_active, processing_enabled)
        query = f"SELECT COUNT(*) FROM stream_sniper.tracked_streamers ts {where_clause}"

        cursor.execute(query, params)
        result = cursor.fetchone()
        return result[0] if result else 0


def update_tracked_streamer_check_time_db(tracked_streamer_id: int, check_time: datetime) -> bool:
    return update_tracked_streamer_db(tracked_streamer_id, last_stream_check=check_time)


def select_active_tracked_streamers_db() -> list[TrackedStreamer]:
    page_size = 500
    offset = 0
    streamers: list[TrackedStreamer] = []
    while True:
        page = select_tracked_streamers_db(
            limit=page_size,
            offset=offset,
            is_active=True,
            processing_enabled=True,
        )
        streamers.extend(page)
        if len(page) < page_size:
            return streamers
        offset += page_size


def streamer_exists_db(twitch_username: str) -> bool:

    with read_cursor() as cursor:
        cursor.execute("SELECT 1 FROM stream_sniper.tracked_streamers WHERE twitch_username = %s", (twitch_username,))
        return cursor.fetchone() is not None
