"""Per-stream rollup recompute (idempotent) + community overlap refresh."""

from ..database.emote_dictionary_table_gateway import select_emote_names_db
from ..database.message_table_gateway import select_stream_phrase_source_db
from ..database.stream_chatter_stats_table_gateway import (
    recompute_stream_rollup_db,
    select_stream_creator_id_db,
)
from ..database.stream_copypasta_stats_table_gateway import (
    replace_stream_copypasta_stats_db,
    select_stream_copypasta_source_db,
)
from ..database.stream_metrics_table_gateway import select_stream_header_db
from ..database.stream_moment_table_gateway import replace_stream_text_rollups_db
from ..database.stream_time_bucket_table_gateway import select_stream_buckets_db
from ..logging_config import get_logger
from . import community, text_stats
from .emote_seed import ensure_emote_dictionary_seeded
from .moment_enrichment import enrich_moments
from .scene_events import refresh_stream_events

logger = get_logger(__name__)

# Recurring-phrase rollup shape (mirrors text_stats.top_phrases defaults).
_PHRASE_LIMIT = 40
_PHRASE_MIN_COUNT = 3


def compute_stream_rollup(stream_id: int, *, refresh_overlap: bool = True) -> None:
    """Recompute all rollup tables for a single stream.

    Stages (each independently try/except-logged, so a partial rollup beats none):
      1. Seed the BTTV emote dictionary if empty (BEFORE TX1, so the emote-stats stage can match).
      2. TX1 — the SQL recompute (buckets, chatter/metrics, creator stats, emote stats).
      3. TX2 — Python-derived phrase + enriched-moment rollups, written together.
      4. Community overlap refresh (non-blocking) when ``refresh_overlap`` is set.

    NOTE: new_chatters / returning_chatters are only correct when streams are rolled up in
    chronological order (oldest first). The bulk/CLI ingest path processes VODs newest-first, so it
    MUST be followed by ``stream-sniper-rollup --all --force``, which re-runs the recompute
    per-creator ascending and overwrites the miscounts.
    """
    row = select_stream_creator_id_db(stream_id)
    if row is None:
        logger.warning(f"compute_stream_rollup: stream {stream_id} not found; skipping")
        return

    creator_id = row[0]
    if creator_id is None:
        logger.warning(f"compute_stream_rollup: stream {stream_id} has no creator_id; skipping")
        return

    try:
        ensure_emote_dictionary_seeded()
    except Exception as e:
        logger.error(f"compute_stream_rollup: emote seed failed for stream {stream_id}: {e}", exc_info=True)

    try:
        recompute_stream_rollup_db(stream_id, creator_id)
    except Exception as e:
        logger.error(f"compute_stream_rollup: SQL recompute failed for stream {stream_id}: {e}", exc_info=True)

    try:
        _compute_and_store_text_rollups(stream_id)
    except Exception as e:
        logger.error(f"compute_stream_rollup: text rollups failed for stream {stream_id}: {e}", exc_info=True)

    try:
        _compute_and_store_copypasta_rollup(stream_id)
    except Exception as e:
        logger.error(
            f"compute_stream_rollup: copypasta rollup failed for stream {stream_id}: {e}", exc_info=True
        )

    try:
        refresh_stream_events(stream_id)
    except Exception as e:
        logger.error(f"compute_stream_rollup: scene events failed for stream {stream_id}: {e}", exc_info=True)

    if refresh_overlap:
        try:
            community.recompute_creator_overlap(blocking=False)
        except Exception as e:
            logger.error(f"compute_stream_rollup: overlap refresh failed for stream {stream_id}: {e}", exc_info=True)


def _compute_and_store_text_rollups(stream_id: int) -> None:
    """TX2: compute phrases + enriched moments in Python, then write both in one transaction."""
    emote_names = {name.lower() for name in select_emote_names_db()}

    phrase_source = select_stream_phrase_source_db(stream_id)
    usage, chatters = text_stats.phrase_stats(phrase_source, emote_names)
    phrase_rows = [
        (phrase, count, len(chatters[phrase])) for phrase, count in usage.items() if count >= _PHRASE_MIN_COUNT
    ]
    phrase_rows.sort(key=lambda item: (-item[1], item[0]))
    phrase_rows = phrase_rows[:_PHRASE_LIMIT]

    header = select_stream_header_db(stream_id)
    stream_start = header[0] if header else None
    buckets = select_stream_buckets_db(stream_id)
    moment_rows = enrich_moments(stream_id, buckets, stream_start, usage, emote_names)

    replace_stream_text_rollups_db(stream_id, phrase_rows, moment_rows)


def _compute_and_store_copypasta_rollup(stream_id: int) -> None:
    """Fill stream_copypasta_stats for a stream from its own bot/junk-filtered SQL source.

    Whole-message copypasta identity (keyed on message_text_id), separate from the tokenized
    phrase rollup. Runs inside the per-stream flow, so `stream-sniper-rollup --all --force`
    backfills it for free.
    """
    rows = select_stream_copypasta_source_db(stream_id)
    replace_stream_copypasta_stats_db(stream_id, rows)
