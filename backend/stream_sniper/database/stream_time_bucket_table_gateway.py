from .decorators import with_cursor


@with_cursor
def select_stream_buckets_db(stream_id, cursor):
    cursor.execute(
        """
        SELECT TO_CHAR(bucket_minute, 'YYYY-MM-DD"T"HH24:MI:SS'), message_count, unique_chatters
        FROM stream_time_bucket
        WHERE stream_id = %s
        ORDER BY bucket_minute ASC
        """,
        (stream_id,),
    )
    return cursor.fetchall()
