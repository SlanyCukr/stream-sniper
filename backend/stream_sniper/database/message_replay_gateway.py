from .decorators import with_cursor


@with_cursor
def select_stream_messages_db(stream_id, limit, cursor, *, after_ts=None, after_id=None, chatter_id=None, q=None):
    conditions = ["m.stream_id = %s"]
    params = [stream_id]

    if after_ts is not None and after_id is not None:
        conditions.append("(m.time, m.id) > (%s::timestamp, %s)")
        params.append(after_ts)
        params.append(after_id)

    if chatter_id is not None:
        conditions.append("m.chatter_id = %s")
        params.append(chatter_id)

    if q is not None:
        conditions.append("mt.text ILIKE %s")
        params.append(f"%{q}%")

    query = (
        'SELECT m.id, TO_CHAR(m.time, \'YYYY-MM-DD"T"HH24:MI:SS\'), m.chatter_id, c.nick, mt.text\n'
        "FROM message m\n"
        "JOIN chatter c ON c.id = m.chatter_id\n"
        "JOIN message_text mt ON mt.id = m.message_text_id\n"
        f"WHERE {' AND '.join(conditions)}\n"
        "ORDER BY m.time ASC, m.id ASC\n"
        "LIMIT %s"
    )
    params.append(limit)

    cursor.execute(query, tuple(params))
    return cursor.fetchall()
