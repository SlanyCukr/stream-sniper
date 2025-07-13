from datetime import datetime

from ..database.stream_table_gateway import insert_stream_db
import logging

from .utils import add_timedelta_to_point_in_time


def update_stream_info(twitch_stream_id: int, started_at: datetime, creator_id: int, title: str, duration: str, thumbnail_url: str):
    logging.debug("Updating stream info.")

    stopped_at = add_timedelta_to_point_in_time(started_at, duration)

    return insert_stream_db(
        twitch_stream_id,
        started_at,
        creator_id,
        title,
        stopped_at,
        thumbnail_url,
    )
