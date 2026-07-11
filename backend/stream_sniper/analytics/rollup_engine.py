"""Per-stream rollup recompute (idempotent)."""

from ..database.stream_chatter_stats_table_gateway import (
    recompute_stream_rollup_db,
    select_stream_creator_id_db,
)
from ..logging_config import get_logger

logger = get_logger(__name__)


def compute_stream_rollup(stream_id: int) -> None:
    """Recompute all rollup tables for a single stream.

    Reads the stream's creator_id, then runs the four-statement recompute in one
    transaction (§4.2). Safe to re-run: every statement is a full DELETE+INSERT /
    UPSERT recompute, so unchanged message data yields identical rollups.

    NOTE: new_chatters / returning_chatters are only correct when streams are rolled
    up in chronological order (oldest first). The bulk/CLI ingest path processes VODs
    newest-first, so it MUST be followed by `stream-sniper-rollup --all --force`, which
    re-runs the recompute per-creator ascending and overwrites the miscounts.
    """
    row = select_stream_creator_id_db(stream_id)
    if row is None:
        logger.warning(f"compute_stream_rollup: stream {stream_id} not found; skipping")
        return

    creator_id = row[0]
    if creator_id is None:
        logger.warning(f"compute_stream_rollup: stream {stream_id} has no creator_id; skipping")
        return

    recompute_stream_rollup_db(stream_id, creator_id)
