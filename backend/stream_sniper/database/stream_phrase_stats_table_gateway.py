from .decorators import with_cursor


@with_cursor
def select_stream_phrases_db(stream_id, limit, cursor):
    cursor.execute(
        """
        SELECT phrase, usage_count, chatter_count
        FROM stream_phrase_stats
        WHERE stream_id = %s
        ORDER BY usage_count DESC, phrase ASC
        LIMIT %s
        """,
        (stream_id, limit),
    )
    return cursor.fetchall()
