from psycopg2.extensions import cursor as Cursor

from stream_sniper.database.gateways.creators.records import ChatterLoyaltyRow, CreatorRegularRow

from ...core.decorators import with_cursor
from ...core.query_ordering import sql_direction
from ...core.wire_format import to_char_wire

# Hardcoded sort whitelist: user-supplied ordering values map through these dicts to a
# fixed SQL fragment, so no user string is ever interpolated into the query.
_REGULAR_SORT = {
    "attendance": "streams_attended",
    "streams": "streams_attended",
    "last_seen": "last_seen_at",
    "messages": "total_messages",
}


@with_cursor
def select_creator_regulars_db(
    cursor: Cursor,
    creator_id: int,
    min_streams: int,
    limit: int,
    *,
    sort: str = "attendance",
    direction: str = "desc",
    include_bots: bool = False,
) -> list[CreatorRegularRow]:
    col = _REGULAR_SORT.get(sort, "streams_attended")
    sql_order = sql_direction(direction)
    # By default bots are hidden from the regulars list; include_bots=True keeps them.
    bot_filter = "" if include_bots else "AND c.is_bot IS NOT TRUE"
    cursor.execute(
        f"""
        SELECT
            ccs.chatter_id,
            c.nick,
            ccs.streams_attended,
            {to_char_wire("ccs.first_seen_at")},
            {to_char_wire("ccs.last_seen_at")},
            ccs.last_seen_stream_id,
            ccs.total_messages
        FROM creator_chatter_stats ccs
        JOIN chatter c ON c.id = ccs.chatter_id
        WHERE ccs.creator_id = %s AND ccs.streams_attended >= %s {bot_filter}
        ORDER BY {col} {sql_order}, ccs.chatter_id ASC
        LIMIT %s
        """,
        (creator_id, min_streams, limit),
    )
    return [CreatorRegularRow(*row) for row in cursor.fetchall()]


@with_cursor
def select_chatter_loyalty_db(
    cursor: Cursor,
    chatter_id: int,
) -> list[ChatterLoyaltyRow]:
    """Every creator a chatter has chatted in, most messages first.

    Reads only the small creator_chatter_stats rollup (no message scan); one row per
    creator the chatter appears in, carrying the per-creator message and attendance
    aggregates plus the first/last-seen wire timestamps (NULL = unknown era).
    """
    cursor.execute(
        f"""
        SELECT
            ccs.creator_id,
            cr.nick,
            cr.display_name,
            ccs.total_messages,
            ccs.streams_attended,
            {to_char_wire("ccs.first_seen_at")},
            {to_char_wire("ccs.last_seen_at")}
        FROM creator_chatter_stats ccs
        JOIN creator cr ON cr.id = ccs.creator_id
        WHERE ccs.chatter_id = %s
        ORDER BY ccs.total_messages DESC, ccs.creator_id ASC
        """,
        (chatter_id,),
    )
    return [ChatterLoyaltyRow(*row) for row in cursor.fetchall()]
