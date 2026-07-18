"""Per-stream rollup recompute (idempotent) + community overlap refresh."""

from collections.abc import Callable
from dataclasses import dataclass

from ...database.gateways.analytics.stream_chatter_stats_table_gateway import (
    recompute_stream_rollup_db,
    select_stream_creator_id_db,
)
from ...database.gateways.analytics.stream_metrics_table_gateway import (
    select_stream_header_db,
    touch_stream_rollup_version_db,
)
from ...database.gateways.analytics.stream_time_bucket_table_gateway import select_stream_buckets_db
from ...database.gateways.chat.emote_dictionary_table_gateway import select_emote_names_db
from ...database.gateways.chat.message_table_gateway import select_stream_phrase_source_db
from ...database.gateways.content.stream_copypasta_stats_table_gateway import (
    replace_stream_copypasta_stats_db,
    select_stream_copypasta_source_db,
)
from ...database.gateways.content.stream_moment_table_gateway import replace_stream_text_rollups_db
from ...logging_config import get_logger
from ..calculations import text_stats
from . import community
from .emote_seed import ensure_emote_dictionary_seeded
from .moment_enrichment import enrich_moments
from .scene_events import refresh_stream_events

logger = get_logger(__name__)

# Recurring-phrase rollup shape (mirrors text_stats.top_phrases defaults).
_PHRASE_LIMIT = 40
_PHRASE_MIN_COUNT = 3


@dataclass(frozen=True)
class RollupPhaseFailure:
    phase: str
    message: str


@dataclass(frozen=True)
class RollupOutcome:
    stream_id: int
    completed_phases: tuple[str, ...] = ()
    failures: tuple[RollupPhaseFailure, ...] = ()
    skipped_reason: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.skipped_reason is None and not self.failures

    def require_success(self) -> None:
        if self.succeeded:
            return
        details = self.skipped_reason or "; ".join(f"{failure.phase}: {failure.message}" for failure in self.failures)
        raise RollupIncompleteError(f"Rollup for stream {self.stream_id} incomplete: {details}")


class RollupIncompleteError(RuntimeError):
    """Raised when a caller requires a complete rollup but one or more phases failed."""


def _run_phase(
    stream_id: int,
    phase: str,
    operation: Callable[[], object],
    completed: list[str],
    failures: list[RollupPhaseFailure],
) -> None:
    try:
        result = operation()
        if result is False:
            failures.append(RollupPhaseFailure(phase=phase, message="skipped because its lock was unavailable"))
            return
        completed.append(phase)
    except Exception as exc:
        failures.append(RollupPhaseFailure(phase=phase, message=str(exc)))
        logger.exception("Rollup phase %s failed for stream %s", phase, stream_id)


def compute_stream_rollup(stream_id: int, *, refresh_overlap: bool = True) -> RollupOutcome:
    """Recompute all rollup tables for a single stream.

    Phases are attempted independently, so a partial rollup beats none. Every
    successful phase appears in ``completed_phases`` and every failed phase is
    reported in ``failures``:
      1. Seed the BTTV emote dictionary if empty (BEFORE TX1, so the emote-stats stage can match).
      2. TX1 — the SQL recompute (buckets, chatter/metrics, creator stats, emote stats).
      3. TX2 — Python-derived phrase + enriched-moment rollups, written together.
      4. Copypasta rollup replacement.
      5. Scene-event derivation and replacement.
      6. Community overlap refresh (non-blocking) when ``refresh_overlap`` is set.

    NOTE: new_chatters / returning_chatters are only correct when streams are rolled up in
    chronological order (oldest first). The bulk/CLI ingest path processes VODs newest-first, so it
    MUST be followed by ``stream-sniper-rollup --all --force``, which re-runs the recompute
    per-creator ascending and overwrites the miscounts.
    """
    try:
        row = select_stream_creator_id_db(stream_id)
    except Exception as exc:
        logger.exception("Rollup stream lookup failed for stream %s", stream_id)
        return RollupOutcome(
            stream_id=stream_id,
            failures=(RollupPhaseFailure("stream_lookup", str(exc)),),
        )
    if row is None:
        logger.warning(f"compute_stream_rollup: stream {stream_id} not found; skipping")
        return RollupOutcome(stream_id=stream_id, skipped_reason="stream not found")

    creator_id = row[0]
    if creator_id is None:
        logger.warning(f"compute_stream_rollup: stream {stream_id} has no creator_id; skipping")
        return RollupOutcome(stream_id=stream_id, skipped_reason="stream has no creator")

    completed: list[str] = []
    failures: list[RollupPhaseFailure] = []
    _run_phase(
        stream_id,
        "emote_seed",
        ensure_emote_dictionary_seeded,
        completed,
        failures,
    )
    _run_phase(
        stream_id,
        "sql_rollup",
        lambda: recompute_stream_rollup_db(stream_id, creator_id),
        completed,
        failures,
    )
    _run_phase(
        stream_id,
        "text_rollups",
        lambda: _compute_and_store_text_rollups(stream_id),
        completed,
        failures,
    )
    _run_phase(
        stream_id,
        "copypasta_rollup",
        lambda: _compute_and_store_copypasta_rollup(stream_id),
        completed,
        failures,
    )
    _run_phase(
        stream_id,
        "scene_events",
        lambda: refresh_stream_events(stream_id),
        completed,
        failures,
    )
    if refresh_overlap:
        _run_phase(
            stream_id,
            "community_overlap",
            lambda: community.recompute_creator_overlap(blocking=False),
            completed,
            failures,
        )

    return RollupOutcome(
        stream_id=stream_id,
        completed_phases=tuple(completed),
        failures=tuple(failures),
    )


def refresh_stream_copypasta_and_events(stream_id: int) -> None:
    """Recompute one stream's copypasta rollup and its derived scene events.

    Targeted alternative to a full ``compute_stream_rollup``: used after bot
    classification so freshly-marked bots drop out of the copypasta source (the
    SQL re-applies the ``is_bot`` filter) and the copypasta_spread events stop
    referencing their texts. Per-stream factual rollups are left untouched, but
    the stream's rollup version IS bumped: the API's scene caches (copypastas,
    trending, wrapped, ...) key on ``stream_metrics.computed_at``, and without
    the touch they would serve the superseded lists for their full TTL.
    """
    _compute_and_store_copypasta_rollup(stream_id)
    refresh_stream_events(stream_id)
    touch_stream_rollup_version_db(stream_id)


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
