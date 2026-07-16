"""
Cross-process liveness heartbeat for the tracking service (Postgres-backed).

The tracking scheduler runs in its own process/container (`stream-sniper-tracking`),
separate from the API. The admin dashboard needs to know whether monitoring is
actually alive, but the two processes don't share memory. Both already connect to
PostgreSQL, so the tracking process upserts a status snapshot into
`stream_sniper.tracking_heartbeat` and the API reads it back with a freshness check.
"""

from pydantic import ValidationError

from ..database.gateways.tracking.tracking_heartbeat_table_gateway import (
    delete_heartbeat_db,
    select_heartbeat_db,
    upsert_heartbeat_db,
)
from .status import HeartbeatSnapshot, HeartbeatState, TrackingStatus

# Single-row component key for the tracking service's heartbeat.
HEARTBEAT_COMPONENT = "tracking"

# How often the tracking process publishes a heartbeat (seconds).
HEARTBEAT_INTERVAL = 15

# A heartbeat older than this (DB-clock seconds) is treated as dead. 3x the
# interval tolerates a slow write / GC pause without flapping while still catching
# a dead or hung process within ~45s.
HEARTBEAT_STALE_AFTER = 45


def write_heartbeat(status: TrackingStatus) -> bool:
    """Publish a status snapshot (stamped with the DB clock). Returns success."""
    return upsert_heartbeat_db(HEARTBEAT_COMPONENT, status.model_dump(mode="json"))


def read_heartbeat() -> HeartbeatSnapshot:
    """Read the latest heartbeat.

    Missing, stale, and schema-incompatible payloads remain distinct. Database
    failures propagate so callers do not mistake an unavailable DB for a dead
    tracking service.
    """
    row = select_heartbeat_db(HEARTBEAT_COMPONENT)
    if row is None:
        return HeartbeatSnapshot(state=HeartbeatState.MISSING)

    payload, age_seconds = row
    try:
        status = TrackingStatus.model_validate(payload)
    except ValidationError as exc:
        return HeartbeatSnapshot(
            state=HeartbeatState.INCOMPATIBLE,
            age_seconds=age_seconds,
            validation_error=str(exc),
        )

    alive = age_seconds <= HEARTBEAT_STALE_AFTER
    return HeartbeatSnapshot(
        state=HeartbeatState.FRESH if alive else HeartbeatState.STALE,
        status=status,
        age_seconds=age_seconds,
        alive=alive,
    )


def delete_heartbeat() -> bool:
    """Remove the heartbeat row so the dashboard reflects 'down' immediately."""
    return delete_heartbeat_db(HEARTBEAT_COMPONENT)
