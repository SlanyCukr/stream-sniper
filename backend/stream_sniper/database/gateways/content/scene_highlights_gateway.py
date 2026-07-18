"""Database gateway for the scene-wide Highlights Wall (hype-ranked moments).

Reads persisted, enriched moments (`stream_moment`) across every creator, joined to
their stream + creator context and their optional human curation (`moment_review`).
Rejected moments are excluded; the caller chooses a hype or recency ordering and an
optional creator / time-window filter. Read-only — curation writes live in
`moment_review_table_gateway`, never here.
"""

from typing import NamedTuple

from psycopg2.extensions import cursor as Cursor

from stream_sniper.database.gateways.content.records import (
    SampleMessagePayload,
    TopPhrasePayload,
)

from ...core.decorators import with_cursor
from ...core.wire_format import to_char_wire

# Hardcoded ORDER BY whitelist: the caller-supplied sort maps through this dict to a fixed
# SQL fragment, so no user string is ever interpolated into the query.
#   hype   -> biggest spike first (ratio, NULLS LAST — a NULL ratio means "no baseline",
#             not "infinite hype"), then busiest minute, then the (stream_id, bucket_minute)
#             primary key so the ordering is total and OFFSET pages never overlap
#   recent -> newest moment minute first, then a stable stream tiebreak
_SORT_CLAUSE = {
    "hype": "m.ratio DESC NULLS LAST, m.message_count DESC, m.stream_id DESC, m.bucket_minute DESC",
    "recent": "m.bucket_minute DESC, m.stream_id DESC",
}


class SceneHighlightRow(NamedTuple):
    """One scene-wide highlight: an enriched moment with stream/creator/curation context."""

    stream_id: int
    stream_title: str
    twitch_id: int | None
    creator_id: int
    creator_nick: str
    creator_display_name: str
    bucket_minute: str
    offset_seconds: int
    ratio: float | None
    message_count: int
    unique_chatters: int
    sub_share: float | None
    emote_share: float | None
    top_phrases: list[TopPhrasePayload] | None
    sample_messages: list[SampleMessagePayload] | None
    clip_url: str | None
    review_status: str | None


@with_cursor
def select_scene_highlights_db(
    cursor: Cursor,
    window_days: int | None,
    creator_id: int | None,
    sort: str,
    limit: int,
    offset: int,
) -> tuple[list[SceneHighlightRow], bool]:
    """Page of scene-wide highlights, hype- or recency-ranked.

    `window_days` restricts to streams started within the trailing window (None = all-time);
    `creator_id` (optional) restricts to one creator. Rejected moments are always excluded
    (`mr.status IS DISTINCT FROM 'rejected'` — a moment with no review row is kept, since
    NULL IS DISTINCT FROM 'rejected' is true). `sort` maps through a hardcoded whitelist.

    Fetches `limit + 1` rows to detect a further page: returns (rows[:limit], has_more).
    """
    order_by = _SORT_CLAUSE[sort]

    filters = ["mr.status IS DISTINCT FROM 'rejected'"]
    params: dict[str, int] = {}
    if window_days is not None:
        filters.append("s.start >= (now() AT TIME ZONE 'UTC') - (%(window_days)s * interval '1 day')")
        params["window_days"] = window_days
    if creator_id is not None:
        filters.append("s.creator_id = %(creator_id)s")
        params["creator_id"] = creator_id

    where_sql = " AND ".join(filters)
    page_params = {**params, "limit": limit + 1, "offset": offset}

    cursor.execute(
        f"""
        SELECT
            m.stream_id,
            s.title,
            s.twitch_id,
            cr.id,
            cr.nick,
            cr.display_name,
            {to_char_wire("m.bucket_minute")},
            m.offset_seconds,
            m.ratio::double precision,
            m.message_count,
            m.unique_chatters,
            m.sub_share::double precision,
            m.emote_share::double precision,
            m.top_phrases,
            m.sample_messages,
            mr.clip_url,
            mr.status
        FROM stream_moment m
        JOIN stream s ON s.id = m.stream_id
        JOIN creator cr ON cr.id = s.creator_id
        LEFT JOIN moment_review mr
            ON mr.stream_id = m.stream_id AND mr.bucket_minute = m.bucket_minute
        WHERE {where_sql}
        ORDER BY {order_by}
        LIMIT %(limit)s OFFSET %(offset)s
        """,
        page_params,
    )
    rows = [SceneHighlightRow(*row) for row in cursor.fetchall()]
    has_more = len(rows) > limit
    return rows[:limit], has_more
