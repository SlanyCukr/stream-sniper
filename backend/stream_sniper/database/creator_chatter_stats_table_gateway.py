from .decorators import with_cursor

# Hardcoded sort whitelist: user-supplied `sort`/`dir` map through these dicts to a
# fixed SQL fragment, so no user string is ever interpolated into the query.
_REGULAR_SORT = {
    "attendance": "streams_attended",
    "streams": "streams_attended",
    "last_seen": "last_seen_at",
    "messages": "total_messages",
}
_DIR = {"asc": "ASC", "desc": "DESC"}


@with_cursor
def select_creator_regulars_db(creator_id, min_streams, limit, cursor, *, sort="attendance", dir="desc"):
    col = _REGULAR_SORT.get(sort, "streams_attended")
    direction = _DIR.get(dir, "DESC")
    cursor.execute(
        f"""
        SELECT
            ccs.chatter_id,
            c.nick,
            ccs.streams_attended,
            TO_CHAR(ccs.first_seen_at, 'YYYY-MM-DD"T"HH24:MI:SS'),
            TO_CHAR(ccs.last_seen_at, 'YYYY-MM-DD"T"HH24:MI:SS'),
            ccs.last_seen_stream_id,
            ccs.total_messages
        FROM creator_chatter_stats ccs
        JOIN chatter c ON c.id = ccs.chatter_id
        WHERE ccs.creator_id = %s AND ccs.streams_attended >= %s
        ORDER BY {col} {direction}, ccs.chatter_id ASC
        LIMIT %s
        """,
        (creator_id, min_streams, limit),
    )
    return cursor.fetchall()
