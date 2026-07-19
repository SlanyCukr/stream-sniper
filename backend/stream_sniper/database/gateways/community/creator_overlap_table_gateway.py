"""Database gateway for community-overlap rollups (creator_audience + creator_overlap).

recompute_creator_overlap_db rebuilds both tables from creator_chatter_stats in one
transaction. It is a global recompute triggered after per-stream rollups, so it is guarded
by a transaction-scoped advisory lock: the hot ingest path uses pg_try_advisory_xact_lock
(skip if another recompute holds it — staleness of one stream is acceptable), while the
end-of-backfill pass takes the blocking pg_advisory_xact_lock (final correctness matters).
"""

from psycopg2.extensions import connection as Connection
from psycopg2.extensions import cursor as Cursor

from stream_sniper.database.gateways.community.records import (
    CommunityCreatorRow,
    CommunityPairRow,
    CreatorNeighborRow,
)

from ...core.decorators import with_cursor, with_cursor_connection
from ...core.wire_format import to_char_wire

# Constant advisory-lock key shared by every overlap recompute (blueprint).
_OVERLAP_LOCK_KEY = 730001

# Hardcoded sort whitelist: the caller-supplied metric maps through this dict to a fixed
# column name, so no user string is ever interpolated into the query.
_NEIGHBOR_METRIC = {
    "shared_chatters": "shared_chatters",
    "shared_regulars": "shared_regulars",
}


@with_cursor_connection
def recompute_creator_overlap_db(
    cursor: Cursor,
    connection: Connection,
    blocking: bool,
) -> bool:
    """Rebuild creator_audience + creator_overlap. Returns False if the lock was contended.

    With blocking=False the advisory lock is tried non-blockingly and a miss returns False
    (the transaction is rolled back to release it); with blocking=True it waits.
    """
    if blocking:
        cursor.execute("SELECT pg_advisory_xact_lock(%s)", (_OVERLAP_LOCK_KEY,))
    else:
        cursor.execute("SELECT pg_try_advisory_xact_lock(%s)", (_OVERLAP_LOCK_KEY,))
        lock_row = cursor.fetchone()
        if lock_row is None:
            raise RuntimeError("overlap advisory lock query returned no row")
        if not bool(lock_row[0]):
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
def select_overlap_db(
    cursor: Cursor,
    limit: int,
) -> tuple[list[CommunityCreatorRow], list[CommunityPairRow]]:
    """Return (creators, pairs): the top-`limit` creators by audience and the pairs among them.

    creators rows: (creator_id, nick, display_name, chatters, regulars, computed_at).
    pairs rows:    (creator_a, creator_b, shared_chatters, shared_regulars).
    """
    cursor.execute(
        f"""
        SELECT ca.creator_id, c.nick, c.display_name, ca.chatters, ca.regulars,
               {to_char_wire("ca.computed_at")}
        FROM creator_audience ca
        JOIN creator c ON c.id = ca.creator_id
        ORDER BY ca.chatters DESC, ca.creator_id ASC
        LIMIT %s
        """,
        (limit,),
    )
    creators = [CommunityCreatorRow(*row) for row in cursor.fetchall()]
    if not creators:
        return [], []

    ids = [row.creator_id for row in creators]
    cursor.execute(
        """
        SELECT creator_a, creator_b, shared_chatters, shared_regulars
        FROM creator_overlap
        WHERE creator_a = ANY(%s) AND creator_b = ANY(%s)
        ORDER BY shared_chatters DESC, creator_a ASC, creator_b ASC
        """,
        (ids, ids),
    )
    pairs = [CommunityPairRow(*row) for row in cursor.fetchall()]
    return creators, pairs


@with_cursor
def select_creator_neighbors_db(
    cursor: Cursor,
    creator_id: int,
    metric: str,
    limit: int,
) -> list[CreatorNeighborRow]:
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
    return [CreatorNeighborRow(*row) for row in cursor.fetchall()]


@with_cursor
def select_creator_audiences_db(
    cursor: Cursor,
    creator_ids: list[int],
) -> list[CommunityCreatorRow]:
    """Audience rollup rows for specific creators (head-to-head denominators)."""
    if not creator_ids:
        return []
    cursor.execute(
        f"""
        SELECT ca.creator_id, c.nick, c.display_name, ca.chatters, ca.regulars,
               {to_char_wire("ca.computed_at")}
        FROM creator_audience ca
        JOIN creator c ON c.id = ca.creator_id
        WHERE ca.creator_id = ANY(%s)
        ORDER BY ca.creator_id ASC
        """,
        (creator_ids,),
    )
    return [CommunityCreatorRow(*row) for row in cursor.fetchall()]


@with_cursor
def select_creator_pair_overlap_db(
    cursor: Cursor,
    creator_a: int,
    creator_b: int,
) -> CommunityPairRow | None:
    """The stored overlap row for one creator pair, or None when never computed.

    ``creator_overlap`` enforces creator_a < creator_b, so the pair is
    normalized before querying.
    """
    lo, hi = sorted((creator_a, creator_b))
    cursor.execute(
        """
        SELECT creator_a, creator_b, shared_chatters, shared_regulars
        FROM creator_overlap
        WHERE creator_a = %s AND creator_b = %s
        """,
        (lo, hi),
    )
    row = cursor.fetchone()
    return CommunityPairRow(*row) if row else None
