"""Database gateway for the emote_dictionary table.

Holds the BTTV seed set plus Twitch emote names learned at collection time. The
provider_id doubles as a CDN URL path segment, so it is regex-validated on the Twitch
upsert path; anything that fails validation is stored NULL (name-only, no image).
"""

import re
from collections.abc import Sequence

from psycopg2.extensions import connection as Connection
from psycopg2.extensions import cursor as Cursor
from psycopg2.extras import execute_values

from ...core.decorators import with_cursor, with_cursor_connection

# provider_id becomes a CDN URL path segment, so it is validated before storage.
_TWITCH_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


def _valid_twitch_id(provider_id: str | None) -> str | None:
    if provider_id is not None and _TWITCH_ID_RE.match(provider_id):
        return provider_id
    return None


@with_cursor_connection
def seed_emote_dictionary_db(
    cursor: Cursor,
    connection: Connection,
    rows: Sequence[tuple[str, str, str | None]],
) -> None:
    """Bulk-seed (name, source, provider_id) rows; existing (name, source) pairs untouched."""
    execute_values(
        cursor,
        """
        INSERT INTO emote_dictionary (name, source, provider_id)
        VALUES %s
        ON CONFLICT (name, source) DO NOTHING
        """,
        rows,
    )
    connection.commit()


@with_cursor_connection
def upsert_twitch_emotes_db(
    cursor: Cursor,
    connection: Connection,
    emotes: Sequence[tuple[str, str | None]],
) -> None:
    """Insert learned Twitch emotes (name, provider_id); invalid ids stored NULL.

    Idempotent: a name already present as a Twitch emote is left as-is (DO NOTHING).
    """
    if not emotes:
        return
    rows = [(name, "twitch", _valid_twitch_id(provider_id)) for name, provider_id in emotes]
    execute_values(
        cursor,
        """
        INSERT INTO emote_dictionary (name, source, provider_id)
        VALUES %s
        ON CONFLICT (name, source) DO NOTHING
        """,
        rows,
    )
    connection.commit()


@with_cursor
def select_dictionary_count_db(
    cursor: Cursor,
    source: str,
) -> int:
    cursor.execute("SELECT count(*) FROM emote_dictionary WHERE source = %s", (source,))
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("emote dictionary count returned no row")
    return int(row[0])


@with_cursor
def select_emote_names_db(
    cursor: Cursor,
) -> list[str]:
    """All distinct emote names (both sources), for filtering emotes out of chat phrases."""
    cursor.execute("SELECT DISTINCT name FROM emote_dictionary")
    return [str(row[0]) for row in cursor.fetchall()]
