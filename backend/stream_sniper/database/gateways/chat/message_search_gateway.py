"""Scene-wide chat search over the deduplicated message_text table.

Match semantics are identical everywhere and mirror revision 0017's index:

    stream_sniper.f_unaccent(lower(mt.text)) LIKE
        '%' || stream_sniper.f_unaccent(lower(%s)) || '%'

Every query runs a two-step plan to stay index-friendly on a large message table:

  1. Resolve matching text ids from message_text via the GIN trigram index, capped
     at ``_MATCH_TEXT_CAP`` ids. The dedup table is ~134k rows, so the cap only bites
     for extremely common substrings.
  2. Join those ids into message (backed by message_text_id_time_idx) for the actual
     hits / counts / per-day buckets.

User input is treated as a literal substring: LIKE wildcards (``%``, ``_``) and the
escape char (``\\``) are neutralized with an explicit ``ESCAPE '\\'`` clause.
"""

from typing import NamedTuple

from psycopg2.extensions import cursor as Cursor

from ...core.decorators import with_cursor

# Cap on matching deduplicated-text ids pulled through the trigram index before the
# join into message. Bounds worst-case work for ultra-common substrings. The capped
# set is ordered by mt.id (DESC for search pages, ASC for origin tracing): text ids
# grow monotonically with first-seen time, so the cap keeps the newest (or oldest)
# distinct texts deterministically instead of an arbitrary planner-dependent subset.
_MATCH_TEXT_CAP = 5000

# Ceiling on per-creator "first match" rows returned by select_first_messages_db.
_BY_CREATOR_LIMIT = 8

_LIKE_MATCH = (
    "stream_sniper.f_unaccent(lower(mt.text)) "
    "LIKE '%%' || stream_sniper.f_unaccent(lower(%s)) || '%%' ESCAPE '\\'"
)

_HIT_COLUMNS = (
    "m.id, "
    "TO_CHAR(m.time, 'YYYY-MM-DD\"T\"HH24:MI:SS.US'), "
    "m.chatter_id, c.nick, c.is_bot, "
    "s.id, s.title, "
    "cr.id, cr.nick, cr.display_name, "
    "mt.text"
)

_HIT_JOINS = (
    "FROM message m\n"
    "JOIN chatter c ON c.id = m.chatter_id\n"
    "JOIN stream s ON s.id = m.stream_id\n"
    "JOIN creator cr ON cr.id = s.creator_id\n"
    "JOIN message_text mt ON mt.id = m.message_text_id"
)


class SearchHitRow(NamedTuple):
    """One matched message joined to its chatter / stream / creator context."""

    message_id: int
    time: str
    chatter_id: int
    chatter_nick: str
    chatter_is_bot: bool | None
    stream_id: int
    stream_title: str
    creator_id: int
    creator_nick: str
    creator_display_name: str
    text: str


class FirstMatchResult(NamedTuple):
    """Origin story of a phrase: earliest hit overall, per-creator debuts, and total."""

    first: SearchHitRow | None
    by_creator: list[SearchHitRow]
    total_matches: int


class TermFrequencyRow(NamedTuple):
    day: str  # 'YYYY-MM-DD'
    count: int


def _escape_like(term: str) -> str:
    r"""Neutralize LIKE metacharacters so user input matches literally.

    Order matters: escape the backslash first, then % and _ (which we escape with
    that same backslash via ESCAPE '\\')."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _matching_text_ids(
    cursor: Cursor,
    query: str,
    *,
    newest_first: bool = True,
    cap: int = _MATCH_TEXT_CAP,
) -> list[int]:
    """Step 1: deduplicated-text ids whose text matches, capped, via the trgm index.

    Ordered by mt.id so the cap is deterministic: ``newest_first=True`` keeps the most
    recently first-seen texts (search pages advertise newest-first), ``False`` keeps
    the earliest first-seen texts (origin tracing needs the oldest candidates).

    Runs on the caller's cursor (NOT independently decorated) so the two-step plan
    holds a single pooled connection per request instead of nesting a second checkout.
    """
    direction = "DESC" if newest_first else "ASC"
    cursor.execute(
        "SELECT mt.id\n"
        "FROM message_text mt\n"
        f"WHERE {_LIKE_MATCH}\n"
        f"ORDER BY mt.id {direction}\n"
        "LIMIT %s",
        (_escape_like(query), cap),
    )
    return [row[0] for row in cursor.fetchall()]


@with_cursor
def search_messages_db(
    cursor: Cursor,
    query: str,
    creator_id: int | None,
    days: int | None,
    limit: int,
    offset: int,
) -> tuple[list[SearchHitRow], bool]:
    """Newest-first page of matching messages plus a has_more sentinel.

    Fetches ``limit + 1`` rows; the caller trims to ``limit`` and reads has_more off
    the overflow row. When a term matches more than ``_MATCH_TEXT_CAP`` distinct
    texts, results cover the most recently first-seen texts (deterministic cap).
    """
    text_ids = _matching_text_ids(cursor, query, newest_first=True)
    if not text_ids:
        return [], False

    conditions = ["m.message_text_id = ANY(%s)"]
    params: list[object] = [text_ids]
    if creator_id is not None:
        conditions.append("s.creator_id = %s")
        params.append(creator_id)
    if days is not None:
        conditions.append("m.time >= (now() AT TIME ZONE 'UTC') - (%s * interval '1 day')")
        params.append(days)

    params.append(limit + 1)
    params.append(offset)
    cursor.execute(
        f"SELECT {_HIT_COLUMNS}\n"
        f"{_HIT_JOINS}\n"
        f"WHERE {' AND '.join(conditions)}\n"
        "ORDER BY m.time DESC, m.id DESC\n"
        "LIMIT %s OFFSET %s",
        tuple(params),
    )
    rows = [SearchHitRow(*row) for row in cursor.fetchall()]
    has_more = len(rows) > limit
    return rows[:limit], has_more


@with_cursor
def select_first_messages_db(
    cursor: Cursor,
    query: str,
    creator_id: int | None,
) -> FirstMatchResult:
    """Earliest overall hit, earliest per-creator debuts (<=8), and total match count.

    The candidate set keeps the EARLIEST first-seen matching texts (``mt.id ASC``), so
    ``first`` is exact even past the cap: if 5000 matching texts predate a candidate's
    text, each of those texts was first used in an earlier matching message, so the true
    origin necessarily lies within the capped set. Per-creator debuts for creators whose
    earliest match uses a text outside the cap are an approximation. ``total_matches``
    is an exact uncapped count (single aggregate, no sort).
    """
    text_ids = _matching_text_ids(cursor, query, newest_first=False)
    if not text_ids:
        return FirstMatchResult(first=None, by_creator=[], total_matches=0)

    scope = ["m.message_text_id = ANY(%s)"]
    scope_params: list[object] = [text_ids]
    if creator_id is not None:
        scope.append("s.creator_id = %s")
        scope_params.append(creator_id)
    where = " AND ".join(scope)

    # Earliest matching message overall.
    cursor.execute(
        f"SELECT {_HIT_COLUMNS}\n"
        f"{_HIT_JOINS}\n"
        f"WHERE {where}\n"
        "ORDER BY m.time ASC, m.id ASC\n"
        "LIMIT 1",
        tuple(scope_params),
    )
    first_row = cursor.fetchone()
    first = SearchHitRow(*first_row) if first_row is not None else None

    # Earliest matching message per creator, then the 8 oldest of those debuts.
    cursor.execute(
        "SELECT * FROM (\n"
        f"  SELECT DISTINCT ON (cr.id) {_HIT_COLUMNS}\n"
        f"  {_HIT_JOINS}\n"
        f"  WHERE {where}\n"
        "  ORDER BY cr.id, m.time ASC, m.id ASC\n"
        ") debut\n"
        # Column 2 is the ISO time string from _HIT_COLUMNS; order debuts oldest-first.
        "ORDER BY 2 ASC\n"
        "LIMIT %s",
        tuple(scope_params) + (_BY_CREATOR_LIMIT,),
    )
    by_creator = [SearchHitRow(*row) for row in cursor.fetchall()]

    # Total matching messages — uncapped: joins the full LIKE match instead of the
    # capped text-id set so the headline count is exact for common terms too.
    count_conditions = [_LIKE_MATCH]
    count_params: list[object] = [_escape_like(query)]
    if creator_id is not None:
        count_conditions.append("s.creator_id = %s")
        count_params.append(creator_id)
    cursor.execute(
        "SELECT count(*)\n"
        "FROM message m\n"
        "JOIN stream s ON s.id = m.stream_id\n"
        "JOIN message_text mt ON mt.id = m.message_text_id\n"
        f"WHERE {' AND '.join(count_conditions)}",
        tuple(count_params),
    )
    count_row = cursor.fetchone()
    total_matches = int(count_row[0]) if count_row is not None else 0

    return FirstMatchResult(first=first, by_creator=by_creator, total_matches=total_matches)


@with_cursor
def select_term_frequency_db(
    cursor: Cursor,
    query: str,
    days: int,
    creator_id: int | None,
) -> list[TermFrequencyRow]:
    """Per-day match counts over the trailing ``days`` window (no zero-fill; API fills).

    The window starts at the beginning of the calendar day ``days - 1`` days ago so
    every bucket — including the oldest — covers a FULL day, matching the API's
    zero-filled date range exactly (a rolling ``now() - days`` bound would truncate
    the oldest bucket mid-day).
    """
    text_ids = _matching_text_ids(cursor, query, newest_first=True)
    if not text_ids:
        return []

    conditions = [
        "m.message_text_id = ANY(%s)",
        "m.time >= date_trunc('day', now() AT TIME ZONE 'UTC') - ((%s - 1) * interval '1 day')",
    ]
    params: list[object] = [text_ids, days]
    if creator_id is not None:
        conditions.append("s.creator_id = %s")
        params.append(creator_id)

    cursor.execute(
        "SELECT TO_CHAR(date_trunc('day', m.time), 'YYYY-MM-DD') AS day, count(*)\n"
        "FROM message m\n"
        "JOIN stream s ON s.id = m.stream_id\n"
        f"WHERE {' AND '.join(conditions)}\n"
        "GROUP BY day\n"
        "ORDER BY day ASC",
        tuple(params),
    )
    return [TermFrequencyRow(day=row[0], count=int(row[1])) for row in cursor.fetchall()]
