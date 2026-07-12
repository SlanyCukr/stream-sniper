"""Database gateway for community-overlap rollups (creator_audience + creator_overlap).

recompute_creator_overlap_db rebuilds both tables from creator_chatter_stats in one
transaction. It is a global recompute triggered after per-stream rollups, so it is guarded
by a transaction-scoped advisory lock: the hot ingest path uses pg_try_advisory_xact_lock
(skip if another recompute holds it — staleness of one stream is acceptable), while the
end-of-backfill pass takes the blocking pg_advisory_xact_lock (final correctness matters).
"""

from .decorators import with_cursor, with_cursor_connection

# Constant advisory-lock key shared by every overlap recompute (blueprint).
_OVERLAP_LOCK_KEY = 730001

# Hardcoded sort whitelist: the caller-supplied metric maps through this dict to a fixed
# column name, so no user string is ever interpolated into the query.
_NEIGHBOR_METRIC = {
    "shared_chatters": "shared_chatters",
    "shared_regulars": "shared_regulars",
}


@with_cursor_connection
def recompute_creator_overlap_db(blocking, cursor, connection):
    """Rebuild creator_audience + creator_overlap. Returns False if the lock was contended.

    With blocking=False the advisory lock is tried non-blockingly and a miss returns False
    (the transaction is rolled back to release it); with blocking=True it waits.
    """
    if blocking:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", (_OVERLAP_LOCK_KEY,))
    else:
        cursor.execute("SELECT pg_try_advisory_xact_lock(%s)", (_OVERLAP_LOCK_KEY,))
        if not cursor.fetchone()[0]:
            connection.rollback()
            return False

    # Bots are excluded from the cross-channel audience/overlap layer (per-stream rollups keep
    # them — that is the factual record). Joining chatter on the (shared) chatter_id and filtering
    # ch.is_bot IS NOT TRUE drops bot chatters from both sides of each pair.
    cursor.execute("DELETE FROM creator_audience")
    cursor.execute(
        """
        INSERT INTO creator_audience (creator_id, chatters, regulars, computed_at)
        SELECT ccs.creator_id, count(*),
               count(*) FILTER (WHERE ccs.streams_attended >= 3), now()
        FROM creator_chatter_stats ccs
        JOIN chatter ch ON ch.id = ccs.chatter_id
        WHERE ch.is_bot IS NOT TRUE
        GROUP BY ccs.creator_id
        """
    )

    cursor.execute("DELETE FROM creator_overlap")
    cursor.execute(
        """
        INSERT INTO creator_overlap
            (creator_a, creator_b, shared_chatters, shared_regulars, computed_at)
        SELECT a.creator_id, b.creator_id,
               count(*),
               count(*) FILTER (WHERE a.streams_attended >= 3 AND b.streams_attended >= 3),
               now()
        FROM creator_chatter_stats a
        JOIN creator_chatter_stats b
            ON b.chatter_id = a.chatter_id AND b.creator_id > a.creator_id
        JOIN chatter ch ON ch.id = a.chatter_id
        WHERE ch.is_bot IS NOT TRUE
        GROUP BY a.creator_id, b.creator_id
        """
    )

    connection.commit()
    return True


@with_cursor
def select_overlap_db(limit, cursor):
    """Return (creators, pairs): the top-`limit` creators by audience and the pairs among them.

    creators rows: (creator_id, nick, display_name, chatters, regulars, computed_at).
    pairs rows:    (creator_a, creator_b, shared_chatters, shared_regulars).
    """
    cursor.execute(
        """
        SELECT ca.creator_id, c.nick, c.display_name, ca.chatters, ca.regulars,
               TO_CHAR(ca.computed_at, 'YYYY-MM-DD"T"HH24:MI:SS')
        FROM creator_audience ca
        JOIN creator c ON c.id = ca.creator_id
        ORDER BY ca.chatters DESC, ca.creator_id ASC
        LIMIT %s
        """,
        (limit,),
    )
    creators = cursor.fetchall()
    if not creators:
        return [], []

    ids = [row[0] for row in creators]
    cursor.execute(
        """
        SELECT creator_a, creator_b, shared_chatters, shared_regulars
        FROM creator_overlap
        WHERE creator_a = ANY(%s) AND creator_b = ANY(%s)
        ORDER BY shared_chatters DESC, creator_a ASC, creator_b ASC
        """,
        (ids, ids),
    )
    pairs = cursor.fetchall()
    return creators, pairs


@with_cursor
def select_creator_neighbors_db(creator_id, metric, limit, cursor):
    """Ranked "audience also watches" neighbors for one creator, reading pairs both ways."""
    col = _NEIGHBOR_METRIC.get(metric, "shared_chatters")
    cursor.execute(
        f"""
        SELECT other.id, other.nick, other.display_name,
               co.shared_chatters, co.shared_regulars
        FROM creator_overlap co
        JOIN creator other ON other.id = CASE
            WHEN co.creator_a = %(cid)s THEN co.creator_b ELSE co.creator_a END
        WHERE co.creator_a = %(cid)s OR co.creator_b = %(cid)s
        ORDER BY co.{col} DESC, other.nick ASC
        LIMIT %(limit)s
        """,
        {"cid": creator_id, "limit": limit},
    )
    return cursor.fetchall()
