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

Bots are excluded at the cross-channel layer (community overlap, regulars) and from the
copypasta rollup; per-stream factual rollups keep them. After a non-dry run this refreshes
the copypasta rollup + scene events for every stream a newly-marked bot spoke in (so stale
bot texts drop out of stream_copypasta_stats) and then triggers a blocking
community-overlap recompute so the exclusion takes effect immediately.
"""

import argparse
from typing import Any

from ...database.core.connection_pool import database_entrypoint
from ...database.gateways.analytics.stream_chatter_stats_table_gateway import (
    select_stream_ids_for_chatters_db,
)
from ...database.gateways.chat.chatter_table_gateway import (
    count_bots_db,
    mark_bots_by_ids_db,
    select_bot_candidates_rate_db,
    select_bot_candidates_ubiquity_db,
    select_unmarked_known_bots_db,
)
from ...logging_config import get_logger, setup_logging
from ..rollups.community import recompute_creator_overlap
from ..rollups.rollup_engine import refresh_stream_copypasta_and_events

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
        # CZ-scene additions confirmed by message content on prod (2026-07-17): song-queue /
        # scene-switch / AFK / relay / ad bots active in tracked Czech channels.
        "supibot",
        "restreambot",
        "botrixoficial",
        "herbot_",
        "spajkk_irl_bot",
    }
)

DEFAULT_MIN_CHANNELS = 20


def classify_bots(min_channels: int = DEFAULT_MIN_CHANNELS, *, dry_run: bool = False) -> dict[str, int]:
    """Run the three classification passes and return a counts summary.

    Returns a dict with keys ``known``, ``ubiquity``, ``rate`` (unmarked candidates found by
    each pass — identical to rows marked on a non-dry run), ``streams_refreshed`` (streams
    whose copypasta rollup + scene events were recomputed because a newly-marked bot spoke
    there; always 0 under dry-run), and ``total_bots`` (chatters currently flagged). With
    ``dry_run`` set no UPDATE runs — the candidate passes are still evaluated and reported.
    """
    newly_marked: list[int] = []

    # Each pass selects-then-marks so dry-run reports real candidates, not list sizes.
    # Candidate rows always lead with the chatter id. Passes:
    #   known    — the curated KNOWN_BOTS name list
    #   ubiquity — cross-channel presence (small creator_chatter_stats rollup)
    #   rate     — superhuman sustained message rate (stream_chatter_stats rollup)
    passes: list[tuple[str, str, list[tuple[int, Any]]]] = [
        ("known", "known_bot", select_unmarked_known_bots_db(sorted(KNOWN_BOTS))),
        ("ubiquity", f"ubiquity:{min_channels}", select_bot_candidates_ubiquity_db(min_channels)),
        ("rate", "rate", select_bot_candidates_rate_db()),
    ]
    counts: dict[str, int] = {}
    for pass_name, reason, candidates in passes:
        counts[pass_name] = len(candidates)
        if not dry_run and candidates:
            ids = [row[0] for row in candidates]
            mark_bots_by_ids_db(ids, reason)
            newly_marked.extend(ids)

    # Newly-marked bots may have contributed texts to stream_copypasta_stats when they were
    # still unclassified; refresh only the streams they spoke in so the rollup re-applies the
    # is_bot filter and derived scene events stop referencing their texts.
    affected_streams = select_stream_ids_for_chatters_db(newly_marked) if newly_marked else []
    for stream_id in affected_streams:
        refresh_stream_copypasta_and_events(stream_id)

    return {
        **counts,
        "streams_refreshed": len(affected_streams),
        "total_bots": count_bots_db(),
    }


@database_entrypoint
def main() -> int:
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

    setup_logging(environment="development")
    logger = get_logger(__name__)

    try:
        counts = classify_bots(args.min_channels, dry_run=args.dry_run)
    except Exception as e:
        logger.error(f"Bot classification failed: {e}", exc_info=True)
        return 1

    prefix = "[dry-run] " if args.dry_run else ""
    logger.info(
        f"{prefix}Bot classification: known={counts['known']}, "
        f"ubiquity={counts['ubiquity']} (>{args.min_channels} channels), "
        f"rate={counts['rate']}; copypasta/scene events refreshed for "
        f"{counts['streams_refreshed']} streams; total bots now {counts['total_bots']}."
    )

    if args.dry_run:
        logger.info("Dry run complete: no rows were modified.")
        return 0

    if args.skip_overlap_recompute:
        logger.info("Skipping community-overlap recompute (--skip-overlap-recompute).")
        return 0

    try:
        recompute_creator_overlap(blocking=True)
        logger.info("Community overlap recomputed (bots now excluded).")
    except Exception as e:
        logger.error(f"Community overlap recompute failed: {e}", exc_info=True)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
