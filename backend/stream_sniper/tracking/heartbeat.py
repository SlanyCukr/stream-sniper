"""
Cross-process liveness heartbeat for the tracking service (Postgres-backed).

The tracking scheduler runs in its own process/container (`stream-sniper-tracking`),
separate from the API. The admin dashboard needs to know whether monitoring is
actually alive, but the two processes don't share memory. Both already connect to
PostgreSQL, so the tracking process upserts a status snapshot into
`stream_sniper.tracking_heartbeat` and the API reads it back with a freshness check.
"""

from typing import Any, Dict, Optional

from ..database.tracking_heartbeat_table_gateway import (
    delete_heartbeat_db,
    select_heartbeat_db,
    upsert_heartbeat_db,
)

# Single-row component key for the tracking service's heartbeat.
HEARTBEAT_COMPONENT = "tracking"

# How often the tracking process publishes a heartbeat (seconds).
HEARTBEAT_INTERVAL = 15

# A heartbeat older than this (DB-clock seconds) is treated as dead. 3x the
# interval tolerates a slow write / GC pause without flapping while still catching
# a dead or hung process within ~45s.
HEARTBEAT_STALE_AFTER = 45


def write_heartbeat(status: Dict[str, Any]) -> bool:
    """Publish a status snapshot (stamped with the DB clock). Returns success."""
    return upsert_heartbeat_db(HEARTBEAT_COMPONENT, status)


def read_heartbeat() -> Optional[Dict[str, Any]]:
    """Read the latest heartbeat.

    Returns ``None`` if the row is absent or the DB is unreachable. Otherwise a
    dict with the published ``status``, its ``age_seconds`` (DB-clock), and an
    ``alive`` flag (fresh within ``HEARTBEAT_STALE_AFTER``).
    """
    row = select_heartbeat_db(HEARTBEAT_COMPONENT)
    if row is None:
        return None

    status, age_seconds = row
    return {
        "status": status or {},
        "age_seconds": age_seconds,
        "alive": age_seconds <= HEARTBEAT_STALE_AFTER,
    }


def delete_heartbeat() -> bool:
    """Remove the heartbeat row so the dashboard reflects 'down' immediately."""
    return delete_heartbeat_db(HEARTBEAT_COMPONENT)
