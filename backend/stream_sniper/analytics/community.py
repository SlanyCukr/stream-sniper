"""Community-overlap recompute wrapper.

Thin orchestration over ``recompute_creator_overlap_db``. On the hot ingest path the recompute is
non-blocking: if another recompute already holds the advisory lock we log and skip (the next stream
end or the end-of-backfill pass refreshes it). The backfill's final pass passes ``blocking=True``.
"""

from ..database.creator_overlap_table_gateway import recompute_creator_overlap_db
from ..logging_config import get_logger

logger = get_logger(__name__)


def recompute_creator_overlap(blocking: bool = False) -> bool:
    """Rebuild the community-overlap tables. Returns True if it ran, False if the lock was skipped.

    With ``blocking=False`` a contended advisory lock is skipped (logged at info); with
    ``blocking=True`` it waits for the lock.
    """
    ran = recompute_creator_overlap_db(blocking)
    if not ran:
        logger.info("Community overlap recompute skipped: another recompute holds the lock")
    return ran
