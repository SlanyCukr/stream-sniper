"""Bot/spam-chatter classification CLI: `stream-sniper-classify-bots`.

Marks chatter rows as bots (chatter.is_bot / bot_reason) using cheap, high-precision
signals that never scan the raw `message` table:

  1. Known-name list (100% precision): a curated set of well-known Twitch service bots,
     matched on lower(nick). Reason ``known_bot``.
  2. Cross-channel ubiquity: chatters present in more than ``--min-channels`` distinct
     creators' audiences (from the creator_chatter_stats rollup). Reason ``ubiquity:<n>``.
  3. Superhuman message rate: chatters sustaining >= 12 msgs/min in >= 3 streams with
     >= 200 messages each (from the stream_chatter_stats rollup). Reason ``rate``.

Marking is monotonic: an already-marked bot is never un-marked or re-reasoned (the gateway
UPDATEs guard on ``is_bot IS NOT TRUE``), so the first classification reason sticks.

Bots are excluded only at the cross-channel layer (community overlap, regulars); per-stream
rollups keep them as the factual record. After a non-dry run this triggers a blocking
community-overlap recompute so the exclusion takes effect immediately.
"""

import argparse
import sys

from dotenv import load_dotenv

from ..database.chatter_table_gateway import (
    count_bots_db,
    mark_bots_by_ids_db,
    mark_bots_by_nick_db,
    select_bot_candidates_rate_db,
    select_bot_candidates_ubiquity_db,
)
from ..logging_config import get_logger, setup_logging
from .community import recompute_creator_overlap

# Well-known Twitch service bots (chat bots, viewer bots, alert/soundboard bots). Matched on
# lower(nick); expand as new ones appear. This is the primary, 100%-precision signal.
KNOWN_BOTS: frozenset[str] = frozenset(
    {
        "nightbot",
        "streamelements",
        "streamlabs",
        "moobot",
        "fossabot",
        "wizebot",
        "botisimo",
        "coebot",
        "deepbot",
        "phantombot",
        "sery_bot",
        "soundalerts",
        "commanderroot",
        "anotherttvviewer",
        "own3d",
        "tangiabot",
        "kofistreambot",
        "blerp",
        "pokemoncommunitygame",
        "sound_alerts",
        "regressz",
        "lurxx",
        "streamholics",
        "aliceydra",
        "creatisbot",
        "tarsai",
        "frostytoolsdotcom",
        "dinu",
        "peepostreambot",
    }
)

DEFAULT_MIN_CHANNELS = 20


def classify_bots(min_channels: int = DEFAULT_MIN_CHANNELS, *, dry_run: bool = False) -> dict:
    """Run the three classification passes and return a counts summary.

    Returns a dict with keys ``known``, ``ubiquity``, ``rate`` (rows marked this run, or the
    candidate count under ``--dry-run``) and ``total_bots`` (chatters currently flagged). With
    ``dry_run`` set no UPDATE runs — the candidate passes are still evaluated and reported.
    """
    counts = {"known": 0, "ubiquity": 0, "rate": 0, "total_bots": 0}

    # 1. Known-name list.
    if dry_run:
        counts["known"] = len(KNOWN_BOTS)
    else:
        counts["known"] = mark_bots_by_nick_db(sorted(KNOWN_BOTS), "known_bot")

    # 2. Cross-channel ubiquity (reads the small creator_chatter_stats rollup).
    ubiquity_candidates = select_bot_candidates_ubiquity_db(min_channels)
    counts["ubiquity"] = len(ubiquity_candidates)
    if not dry_run and ubiquity_candidates:
        mark_bots_by_ids_db([row[0] for row in ubiquity_candidates], f"ubiquity:{min_channels}")

    # 3. Superhuman sustained message rate (reads the stream_chatter_stats rollup).
    rate_candidates = select_bot_candidates_rate_db()
    counts["rate"] = len(rate_candidates)
    if not dry_run and rate_candidates:
        mark_bots_by_ids_db([row[0] for row in rate_candidates], "rate")

    counts["total_bots"] = count_bots_db()
    return counts


def main():
    parser = argparse.ArgumentParser(
        prog="stream-sniper-classify-bots",
        description="Classify chatters as bots via known-name + cross-channel + rate heuristics.",
    )
    parser.add_argument(
        "--min-channels",
        type=int,
        default=DEFAULT_MIN_CHANNELS,
        help=f"Ubiquity threshold: chatters in more than this many distinct creators "
        f"are flagged (default {DEFAULT_MIN_CHANNELS}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be marked without writing any UPDATE.",
    )
    parser.add_argument(
        "--skip-overlap-recompute",
        action="store_true",
        help="Do not recompute community overlap after marking (advanced/testing).",
    )
    args = parser.parse_args()

    load_dotenv()
    setup_logging(environment="development")
    logger = get_logger(__name__)

    try:
        counts = classify_bots(args.min_channels, dry_run=args.dry_run)
    except Exception as e:
        logger.error(f"Bot classification failed: {e}", exc_info=True)
        sys.exit(1)

    prefix = "[dry-run] " if args.dry_run else ""
    logger.info(
        f"{prefix}Bot classification: known={counts['known']}, "
        f"ubiquity={counts['ubiquity']} (>{args.min_channels} channels), "
        f"rate={counts['rate']}; total bots now {counts['total_bots']}."
    )

    if args.dry_run:
        logger.info("Dry run complete: no rows were modified.")
        return

    if args.skip_overlap_recompute:
        logger.info("Skipping community-overlap recompute (--skip-overlap-recompute).")
        return

    try:
        recompute_creator_overlap(blocking=True)
        logger.info("Community overlap recomputed (bots now excluded).")
    except Exception as e:
        logger.error(f"Community overlap recompute failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
