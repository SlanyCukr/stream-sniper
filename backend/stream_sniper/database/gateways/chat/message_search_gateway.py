"""Scene-wide chat search over the deduplicated message_text table.

Match semantics are identical everywhere and mirror revision 0017's index:

    stream_sniper.f_unaccent(lower(mt.text)) LIKE
        '%' || stream_sniper.f_unaccent(lower(%s)) || '%'

The paginated page query runs a two-step plan to stay index-friendly on a large
message table:

  1. Resolve matching text ids from message_text via the GIN trigram index, capped
     at ``_MATCH_TEXT_CAP`` ids WITHIN the requested creator/time scope. The dedup
     table is ~134k rows, so the cap only bites for extremely common substrings.
  2. Join those ids into message (backed by message_text_id_time_idx) for the hits.

The origin (``select_first_messages_db``) and frequency queries run UNCAPPED
against the full LIKE match — single bounded scans whose results must be exact.

User input is treated as a literal substring: LIKE wildcards (``%``, ``_``) and the
escape char (``\\``) are neutralized with an explicit ``ESCAPE '\\'`` clause.
"""

from typing import NamedTuple

from psycopg2.extensions import cursor as Cursor

from ...core.decorators import with_cursor
from ...core.wire_format import to_char_wire_us

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
    f"{to_char_wire_us('m.time')}, "
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
    matches: int  # named "matches", not "count", to avoid shadowing tuple.count


def _escape_like(term: str) -> str:
    r"""Neutralize LIKE metacharacters so user input matches literally.

    Order matters: escape the backslash first, then % and _ (which we escape with
    that same backslash via ESCAPE '\\')."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _matching_text_ids(
    cursor: Cursor,
    query: str,
    *,
    creator_id: int | None = None,
    days: int | None = None,
    cap: int = _MATCH_TEXT_CAP,
) -> list[int]:
    """Step 1: deduplicated-text ids whose text matches, capped, via the trgm index.

    The cap is applied AFTER any creator/time scoping (via an indexed EXISTS probe
    into message), so a creator-scoped search for an ultra-common term can never
    lose that creator's matches to the global cap. Ordered ``mt.id DESC`` so the
    capped set is deterministic and biased toward recently first-seen texts,
    matching the newest-first contract of the paginated search.

    Runs on the caller's cursor (NOT independently decorated) so the two-step plan
    holds a single pooled connection per request instead of nesting a second checkout.
    """
    conditions = [_LIKE_MATCH]
    params: list[object] = [_escape_like(query)]
    scope: list[str] = []
    scope_params: list[object] = []
    if creator_id is not None:
        scope.append("s.creator_id = %s")
        scope_params.append(creator_id)
    if days is not None:
        scope.append("m.time >= (now() AT TIME ZONE 'UTC') - (%s * interval '1 day')")
        scope_params.append(days)
    if scope:
        conditions.append(
            "EXISTS (SELECT 1 FROM message m JOIN stream s ON s.id = m.stream_id\n"
            f"        WHERE m.message_text_id = mt.id AND {' AND '.join(scope)})"
        )
        params.extend(scope_params)

    params.append(cap)
    cursor.execute(
        "SELECT mt.id\n"
        "FROM message_text mt\n"
        f"WHERE {' AND '.join(conditions)}\n"
        "ORDER BY mt.id DESC\n"
        "LIMIT %s",
        tuple(params),
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
    texts WITHIN the requested scope, results cover the most recently first-seen
    texts (deterministic cap; the creator/days filters are pushed into the cap
    query so scoped searches never lose matches to globally-common texts).
    """
    text_ids = _matching_text_ids(cursor, query, creator_id=creator_id, days=days)
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

    All three run UNCAPPED against the full LIKE match (the planner does its own
    two-step: GIN bitmap scan on message_text, then the message_text_id btree into
    message), so ``first``, the per-creator debuts, and ``total_matches`` are exact —
    no dependence on the text-id cap or on message_text.id tracking chronology
    (backfilled VODs can create old messages with high text ids). Cost is one
    bounded scan of the matching messages per query, same class as the count, and
    the endpoint result is TTL-cached.
    """
    conditions = [_LIKE_MATCH]
    params: list[object] = [_escape_like(query)]
    if creator_id is not None:
        conditions.append("s.creator_id = %s")
        params.append(creator_id)
    where = " AND ".join(conditions)

    # Earliest matching message overall (top-1 over the matched set — no sort spill).
    cursor.execute(
        f"SELECT {_HIT_COLUMNS}\n"
        f"{_HIT_JOINS}\n"
        f"WHERE {where}\n"
        "ORDER BY m.time ASC, m.id ASC\n"
        "LIMIT 1",
        tuple(params),
    )
    first_row = cursor.fetchone()
    first = SearchHitRow(*first_row) if first_row is not None else None

    if first is None:
        return FirstMatchResult(first=None, by_creator=[], total_matches=0)

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
        tuple(params) + (_BY_CREATOR_LIMIT,),
    )
    by_creator = [SearchHitRow(*row) for row in cursor.fetchall()]

    # Total matching messages, exact.
    cursor.execute(
        "SELECT count(*)\n"
        "FROM message m\n"
        "JOIN stream s ON s.id = m.stream_id\n"
        "JOIN message_text mt ON mt.id = m.message_text_id\n"
        f"WHERE {where}",
        tuple(params),
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

    Runs UNCAPPED against the full LIKE match (like ``select_first_messages_db``)
    so counts are exact for common terms too — a single bounded aggregate, cached
    at the endpoint.
    """
    conditions = [
        _LIKE_MATCH,
        "m.time >= date_trunc('day', now() AT TIME ZONE 'UTC') - ((%s - 1) * interval '1 day')",
    ]
    params: list[object] = [_escape_like(query), days]
    if creator_id is not None:
        conditions.append("s.creator_id = %s")
        params.append(creator_id)

    cursor.execute(
        "SELECT TO_CHAR(date_trunc('day', m.time), 'YYYY-MM-DD') AS day, count(*)\n"
        "FROM message m\n"
        "JOIN stream s ON s.id = m.stream_id\n"
        "JOIN message_text mt ON mt.id = m.message_text_id\n"
        f"WHERE {' AND '.join(conditions)}\n"
        "GROUP BY day\n"
        "ORDER BY day ASC",
        tuple(params),
    )
    return [TermFrequencyRow(day=row[0], matches=int(row[1])) for row in cursor.fetchall()]
