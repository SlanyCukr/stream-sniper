"""Public read endpoint for the live Moment Radar (chat velocity for currently-live streams).

Public (no auth), following the analytics/scene endpoint conventions: sync ``def`` handler
(psycopg2 blocks), ``request: Request`` + ``response: Response`` for slowapi, and a short
in-process TTL cache. This is a poll surface, not a rollup-versioned one, so it mirrors
``/scene/live``'s plain ``ModelCachePolicy`` (no ``scene_rollup_version`` key) but with a much
shorter TTL — velocity spikes are brief, so a 15s snapshot stays fresh while still cheap.

Single-gateway read: per the project's layering rule, the (pure, unit-testable) assembly of
median baseline / ratio / spike flag / zero-fill lives here in the handler module — there is no
application layer for a one-gateway endpoint. The spike thresholds are reused verbatim from
``analytics/calculations/moments.py`` so radar "spiking" means the same thing as a persisted
moment. The module-level ``router`` name is kept so api.py's registration stays valid.
"""

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from statistics import median

from fastapi import APIRouter, Request, Response

from ....analytics.calculations.moments import MIN_ABSOLUTE, SPIKE_MULTIPLIER
from ....database.core.wire_format import WIRE_TS_FORMAT
from ....database.gateways.content.scene_radar_gateway import (
    LiveStreamRow,
    MinuteCountRow,
    select_live_chat_velocity_db,
)
from ...caching.model_cache import ModelCachePolicy
from ...dependencies import get_cache
from ...security.rate_limiter import limiter, rate_limits
from ...transport.models import RateLimitErrorResponse
from .scene_radar_models import RadarChannel, RadarMinute, SceneRadar

# Fresher than /scene/live's 60s: velocity spikes are short-lived, so a stale radar is worse
# than a stale live-now board. Still a real cache — polling clients share the 15s snapshot.
_RADAR_CACHE_TTL_SECONDS = 15

# 15 completed minutes are rendered; the baseline is the median over all but the last of them,
# and needs at least this many nonzero minutes before it means anything.
_DISPLAY_MINUTES = 15
_BASELINE_MIN_NONZERO = 3

router = APIRouter(tags=["Scene"])

_RADAR_CACHE = ModelCachePolicy("scene_radar", _RADAR_CACHE_TTL_SECONDS, SceneRadar)


def _now_naive_utc() -> datetime:
    """Wall clock as a naive UTC datetime, matching the DB's naive-UTC timestamps."""
    return datetime.now(UTC).replace(tzinfo=None)


def _build_channel(
    live: LiveStreamRow,
    per_minute: dict[str, MinuteCountRow],
    display_minutes: list[datetime],
    last_completed: datetime,
) -> RadarChannel:
    """Assemble one channel's zero-filled series, baseline, ratio, and spike verdict."""
    minute_models: list[RadarMinute] = []
    counts: list[int] = []
    for minute in display_minutes:
        key = minute.strftime(WIRE_TS_FORMAT)
        row = per_minute.get(key)
        messages = row.messages if row is not None else 0
        counts.append(messages)
        minute_models.append(RadarMinute(minute=key, messages=messages))

    last_row = per_minute.get(last_completed.strftime(WIRE_TS_FORMAT))
    messages_last_minute = last_row.messages if last_row is not None else 0
    unique_last_minute = last_row.unique_chatters if last_row is not None else 0

    # Baseline excludes the last (most recent) completed minute — that is the minute being judged.
    # The median is over the NONZERO history minutes: it estimates the stream's typical rate
    # while chat is active. A zero-filled median would collapse to 0 for sparse-but-eligible
    # streams (3-6 active minutes out of 14), silently disabling the ratio for exactly the
    # intermittent activity the _BASELINE_MIN_NONZERO gate is meant to admit.
    history = counts[:-1]
    nonzero_history = [count for count in history if count > 0]
    baseline: float | None = (
        float(median(nonzero_history)) if len(nonzero_history) >= _BASELINE_MIN_NONZERO else None
    )

    # nullable = unknown: a null/zero baseline yields a null ratio, never a fabricated number.
    ratio = round(messages_last_minute / baseline, 2) if baseline else None
    # EXACTLY moments.py's spike test: counts >= max(SPIKE_MULTIPLIER * baseline, MIN_ABSOLUTE).
    # A null baseline (cold start / <3 nonzero minutes) still lets the absolute floor fire —
    # the persisted-moment detector treats an all-zero window as baseline 0 and flags the
    # burst, so a newly-live channel's first big minute must light up here too. ratio stays
    # null for display (there is no meaningful multiplier without a baseline).
    spiking = messages_last_minute >= max(SPIKE_MULTIPLIER * (baseline or 0.0), MIN_ABSOLUTE)

    return RadarChannel(
        stream_id=live.stream_id,
        creator_id=live.creator_id,
        creator_nick=live.creator_nick,
        creator_display_name=live.creator_display_name,
        profile_image_url=live.profile_image_url,
        stream_title=live.stream_title,
        started_at=live.started_at,
        messages_last_minute=messages_last_minute,
        unique_chatters_last_minute=unique_last_minute,
        baseline_per_minute=baseline,
        ratio=ratio,
        spiking=spiking,
        minutes=minute_models,
    )


def build_radar(
    live_rows: list[LiveStreamRow],
    minute_rows: list[MinuteCountRow],
    now: datetime,
) -> SceneRadar:
    """Pure assembly of the radar snapshot from raw gateway rows and the current time.

    The current in-progress minute is partial and excluded: the last judged minute is the last
    COMPLETED minute (``floor(now) - 1min``), and the rendered series is the 15 completed minutes
    ending there, ascending and zero-filled. Channels sort spiking-first, then busiest last minute,
    then stream_id — a total order. Kept DB-free so the velocity math is unit-testable.
    """
    current_minute = now.replace(second=0, microsecond=0)
    last_completed = current_minute - timedelta(minutes=1)
    # Ascending: [last_completed - 14min ... last_completed].
    display_minutes = [last_completed - timedelta(minutes=offset) for offset in reversed(range(_DISPLAY_MINUTES))]

    counts_by_stream: dict[int, dict[str, MinuteCountRow]] = defaultdict(dict)
    for row in minute_rows:
        counts_by_stream[row.stream_id][row.minute] = row

    channels = [
        _build_channel(live, counts_by_stream.get(live.stream_id, {}), display_minutes, last_completed)
        for live in live_rows
    ]
    channels.sort(key=lambda channel: (not channel.spiking, -channel.messages_last_minute, channel.stream_id))

    return SceneRadar(generated_at=now.strftime(WIRE_TS_FORMAT), channels=channels)


@router.get(
    "/scene/radar",
    response_model=SceneRadar,
    summary="Get the live Moment Radar",
    description="Per-minute chat velocity for every currently-live stream, with spikes surfaced first.",
    responses={429: {"model": RateLimitErrorResponse, "description": "Rate limit exceeded"}},
)
@limiter.limit(rate_limits.ANALYTICS)
def get_scene_radar(request: Request, response: Response) -> SceneRadar:
    """Get the live Moment Radar: chat velocity and spike verdicts across live streams."""
    with _RADAR_CACHE.record_failures():
        cache = get_cache(request)
        cache_key, cached = _RADAR_CACHE.lookup(cache, response)
        if cached is not None:
            return cached

        live_rows, minute_rows = select_live_chat_velocity_db()
        result = build_radar(live_rows, minute_rows, _now_naive_utc())
        _RADAR_CACHE.store(cache, response, cache_key, result)
        return result
