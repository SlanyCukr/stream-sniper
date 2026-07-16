from psycopg2.extensions import cursor as Cursor

from stream_sniper.database.gateways.analytics.records import StreamBucketRow

from ...core.decorators import with_cursor


@with_cursor
def select_stream_buckets_db(
    cursor: Cursor,
    stream_id: int,
) -> list[StreamBucketRow]:
    cursor.execute(
        """
        SELECT TO_CHAR(bucket_minute, 'YYYY-MM-DD"T"HH24:MI:SS'), message_count, unique_chatters,
               sub_messages, emote_messages
        FROM stream_time_bucket
        WHERE stream_id = %s
        ORDER BY bucket_minute ASC
        """,
        (stream_id,),
    )
    return [StreamBucketRow(*row) for row in cursor.fetchall()]
