"""
Database gateway for the tracking_heartbeat table (cross-process liveness).

The tracking service upserts one row per component; the API reads it to decide
whether monitoring is alive. age_seconds is computed with the DB clock on both
sides (now() - updated_at), so it is immune to clock skew between the API and
tracking containers.
"""

import json

from ...core.decorators import read_cursor, write_cursor


def upsert_heartbeat_db(component: str, status: dict[str, object]) -> bool:
    """Insert/update a component's heartbeat row, stamping updated_at = now()."""
    if not isinstance(status, dict):
        raise TypeError("tracking heartbeat status must be a JSON object")

    with write_cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO stream_sniper.tracking_heartbeat (component, status, updated_at)
            VALUES (%s, %s::jsonb, now())
            ON CONFLICT (component)
            DO UPDATE SET status = EXCLUDED.status, updated_at = now()
            """,
            (component, json.dumps(status, default=str)),
        )
        return True


def select_heartbeat_db(component: str) -> tuple[dict[str, object] | None, float] | None:
    """Return status and age, or None when absent; database and validation errors propagate."""

    with read_cursor() as cursor:
        cursor.execute(
            """
            SELECT status, EXTRACT(EPOCH FROM (now() - updated_at))
            FROM stream_sniper.tracking_heartbeat
            WHERE component = %s
            """,
            (component,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        status = row[0]
        if status is not None and not isinstance(status, dict):
            raise ValueError("tracking heartbeat status must be a JSON object")
        # psycopg2 parses jsonb -> dict automatically; age arrives as Decimal.
        return status, float(row[1])


def delete_heartbeat_db(component: str) -> bool:
    """Remove a component's heartbeat row (e.g. on graceful shutdown)."""

    with write_cursor() as cursor:
        cursor.execute(
            "DELETE FROM stream_sniper.tracking_heartbeat WHERE component = %s",
            (component,),
        )
        return True
