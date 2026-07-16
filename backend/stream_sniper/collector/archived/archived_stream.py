"""Archived-stream persistence owned by the VOD collector."""

from datetime import datetime, timedelta
from typing import cast

from pytimeparse.timeparse import timeparse  # type: ignore[import-untyped]

from ...database.gateways.streams.stream_table_gateway import insert_stream_db


def _stopped_at(started_at: datetime, duration: str) -> datetime:
    seconds = timeparse(duration)
    if seconds is None:
        raise ValueError(f"Invalid Twitch duration: {duration!r}")
    return started_at + timedelta(seconds=seconds)


def ensure_archived_stream_db(
    twitch_vod_id: int,
    started_at: datetime,
    creator_id: int,
    title: str,
    duration: str,
    thumbnail_url: str,
) -> int:
    return cast(
        int,
        insert_stream_db(
            twitch_vod_id,
            started_at,
            creator_id,
            title,
            _stopped_at(started_at, duration),
            thumbnail_url,
        ),
    )
