from .decorators import with_cursor


@with_cursor
def select_stream_emotes_db(stream_id, limit, cursor):
    cursor.execute(
        """
        SELECT d.name, d.source, d.provider_id, ses.usage_count, ses.chatter_count
        FROM stream_emote_stats ses
        JOIN emote_dictionary d ON d.id = ses.emote_id
        WHERE ses.stream_id = %s
        ORDER BY ses.usage_count DESC, d.name ASC
        LIMIT %s
        """,
        (stream_id, limit),
    )
    return cursor.fetchall()


@with_cursor
def select_creator_emotes_db(creator_id, limit, cursor):
    # Sum a creator's per-stream emote usage across all of their streams; stream_count is
    # the number of distinct streams the emote appeared in.
    cursor.execute(
        """
        SELECT d.name, d.source, d.provider_id,
               sum(ses.usage_count)::bigint AS usage_count,
               sum(ses.chatter_count)::bigint AS chatter_count,
               count(DISTINCT ses.stream_id)::int AS stream_count
        FROM stream_emote_stats ses
        JOIN emote_dictionary d ON d.id = ses.emote_id
        JOIN stream s ON s.id = ses.stream_id
        WHERE s.creator_id = %s
        GROUP BY d.id, d.name, d.source, d.provider_id
        ORDER BY usage_count DESC, d.name ASC
        LIMIT %s
        """,
        (creator_id, limit),
    )
    return cursor.fetchall()
