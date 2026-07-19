"""Pairwise co-attendance for two specific chatters.

Self-joins ``stream_chatter_stats`` on stream_id (the same shape as
``chat_companions_gateway`` but anchored on an explicit pair instead of
ranking companions). A pair that never shared a stream is a legitimate
all-zero row, not an error.
"""

from typing import NamedTuple

from psycopg2.extensions import cursor as Cursor

from ...core.decorators import with_cursor


class ChatterPairSharedRow(NamedTuple):
    """Streams (and distinct channels) both chatters attended."""

    shared_streams: int
    shared_creators: int


@with_cursor
def select_chatter_pair_shared_db(cursor: Cursor, chatter_a: int, chatter_b: int) -> ChatterPairSharedRow:
    """Count streams both chatters attended and the distinct creators those span."""
    cursor.execute(
        """
        SELECT COUNT(*)::int AS shared_streams,
               COUNT(DISTINCT s.creator_id)::int AS shared_creators
        FROM stream_chatter_stats a
        JOIN stream_chatter_stats b
            ON b.stream_id = a.stream_id AND b.chatter_id = %s
        JOIN stream s ON s.id = a.stream_id
        WHERE a.chatter_id = %s
        """,
        (chatter_b, chatter_a),
    )
    row = cursor.fetchone()
    if row is None:  # aggregate always yields one row; guard for the type checker
        return ChatterPairSharedRow(shared_streams=0, shared_creators=0)
    return ChatterPairSharedRow(*row)
