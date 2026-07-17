from psycopg2.extensions import cursor as Cursor

from stream_sniper.database.gateways.analytics.records import StreamBucketRow

from ...core.decorators import with_cursor
from ...core.wire_format import to_char_wire


@with_cursor
def select_stream_buckets_db(
    cursor: Cursor,
    stream_id: int,
) -> list[StreamBucketRow]:
    cursor.execute(
        f"""
        SELECT {to_char_wire("bucket_minute")}, message_count, unique_chatters,
               sub_messages, emote_messages
        FROM stream_time_bucket
        WHERE stream_id = %s
        ORDER BY bucket_minute ASC
        """,
        (stream_id,),
    )
    return [StreamBucketRow(*row) for row in cursor.fetchall()]
