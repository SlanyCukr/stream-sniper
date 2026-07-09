"""
Database gateway for the tracking_heartbeat table (cross-process liveness).

The tracking service upserts one row per component; the API reads it to decide
whether monitoring is alive. age_seconds is computed with the DB clock on both
sides (now() - updated_at), so it is immune to clock skew between the API and
tracking containers.
"""

import json
from typing import Any, Dict, Optional, Tuple

from ..logging_config import get_logger
from .connection_pool import get_pool
from .decorators import log_database_operation

logger = get_logger(__name__)


@log_database_operation
def upsert_heartbeat_db(component: str, status: Dict[str, Any]) -> bool:
    """Insert/update a component's heartbeat row, stamping updated_at = now()."""
    pool = get_pool()

    try:
        with pool.get_cursor(commit=True) as cursor:
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
    except Exception as e:
        logger.error(f"Error upserting heartbeat for {component}: {e}")
        return False


@log_database_operation
def select_heartbeat_db(component: str) -> Optional[Tuple[Any, float]]:
    """Return (status, age_seconds) for a component, or None if absent/on error."""
    pool = get_pool()

    try:
        with pool.get_cursor() as cursor:
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
            # psycopg2 parses jsonb -> dict automatically; age arrives as Decimal.
            return row[0], float(row[1])
    except Exception as e:
        logger.error(f"Error selecting heartbeat for {component}: {e}")
        return None


@log_database_operation
def delete_heartbeat_db(component: str) -> bool:
    """Remove a component's heartbeat row (e.g. on graceful shutdown)."""
    pool = get_pool()

    try:
        with pool.get_cursor(commit=True) as cursor:
            cursor.execute(
                "DELETE FROM stream_sniper.tracking_heartbeat WHERE component = %s",
                (component,),
            )
            return True
    except Exception as e:
        logger.error(f"Error deleting heartbeat for {component}: {e}")
        return False
