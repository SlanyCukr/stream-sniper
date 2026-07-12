"""Backfill CLI for analytics rollups: `stream-sniper-rollup`.

Selects streams chronologically per-creator (ORDER BY creator_id, start ASC, id ASC)
and recomputes each stream's rollups. This ascending order is what makes
new_chatters / returning_chatters correct, so this backfill (with --force) is the
mandatory correctness pass after a bulk `stream-sniper <user>` import.
"""

import argparse
import sys

from dotenv import load_dotenv

from ..database.stream_chatter_stats_table_gateway import select_rollup_stream_ids_db
from ..logging_config import get_logger, setup_logging
from .community import recompute_creator_overlap
from .rollup_engine import compute_stream_rollup


def main():
    parser = argparse.ArgumentParser(
        prog="stream-sniper-rollup",
        description="Recompute analytics rollups for streams (chronological per-creator).",
    )
    parser.add_argument("--creator", metavar="NICK", help="Only roll up streams for this creator nick.")
    parser.add_argument("--all", action="store_true", help="Roll up streams for all creators.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Recompute every selected stream, even ones that already have a stream_metrics row "
        "(the correctness pass; without it, streams already rolled up are skipped).",
    )
    args = parser.parse_args()

    load_dotenv()
    setup_logging(environment="development")
    logger = get_logger(__name__)

    if not args.all and not args.creator:
        parser.print_usage()
        logger.error("Specify --all (every creator) or --creator <nick>.")
        sys.exit(1)

    rows = select_rollup_stream_ids_db(creator_nick=args.creator, force=args.force)
    stream_ids = [row[0] for row in rows]
    logger.info(f"Backfill selected {len(stream_ids)} stream(s) (force={args.force}).")

    processed = 0
    failures = 0
    for stream_id in stream_ids:
        try:
            # Defer the global overlap recompute to a single blocking pass at the end, so it
            # runs once (with correct final data) instead of after every stream.
            compute_stream_rollup(stream_id, refresh_overlap=False)
            processed += 1
        except Exception as e:
            failures += 1
            logger.error(f"Rollup failed for stream {stream_id}: {e}", exc_info=True)

    logger.info(f"Backfill complete: {processed} succeeded, {failures} failed.")

    try:
        recompute_creator_overlap(blocking=True)
        logger.info("Community overlap recomputed.")
    except Exception as e:
        logger.error(f"Community overlap recompute failed: {e}", exc_info=True)

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
