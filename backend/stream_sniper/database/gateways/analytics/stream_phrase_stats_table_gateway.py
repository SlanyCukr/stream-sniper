from psycopg2.extensions import cursor as Cursor

from stream_sniper.database.gateways.analytics.records import TopPhraseRow

from ...core.decorators import with_cursor


@with_cursor
def select_stream_phrases_db(
    cursor: Cursor,
    stream_id: int,
    limit: int,
) -> list[TopPhraseRow]:
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
    return [TopPhraseRow(*row) for row in cursor.fetchall()]
