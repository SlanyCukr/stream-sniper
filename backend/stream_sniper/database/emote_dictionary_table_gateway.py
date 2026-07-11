"""Database gateway for the emote_dictionary table.

Holds the BTTV seed set plus Twitch emote names learned at collection time. The
provider_id doubles as a CDN URL path segment, so it is regex-validated on the Twitch
upsert path; anything that fails validation is stored NULL (name-only, no image).
"""

import re
from typing import List, Optional, Tuple

from psycopg2.extras import execute_values

from .decorators import with_cursor, with_cursor_connection

# provider_id becomes a CDN URL path segment, so it is validated before storage.
_TWITCH_ID_RE = re.compile(r"^[A-Za-z0-9_\-]{1,64}$")


def _valid_twitch_id(provider_id: Optional[str]) -> Optional[str]:
    if provider_id is not None and _TWITCH_ID_RE.match(provider_id):
        return provider_id
    return None


@with_cursor_connection
def seed_emote_dictionary_db(rows: List[Tuple[str, str, Optional[str]]], cursor, connection):
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
def upsert_twitch_emotes_db(emotes: List[Tuple[str, Optional[str]]], cursor, connection):
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
def select_dictionary_count_db(source, cursor):
    cursor.execute("SELECT count(*) FROM emote_dictionary WHERE source = %s", (source,))
    return cursor.fetchone()[0]


@with_cursor
def select_emote_names_db(cursor):
    """All distinct emote names (both sources), for filtering emotes out of chat phrases."""
    cursor.execute("SELECT DISTINCT name FROM emote_dictionary")
    return [row[0] for row in cursor.fetchall()]
