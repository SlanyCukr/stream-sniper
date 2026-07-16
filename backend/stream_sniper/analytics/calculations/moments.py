"""Spike-moment detection over per-minute message buckets.

Pure, dependency-light function used by the timeline endpoint (§4.4). Given the
ascending per-minute buckets already fetched for a stream, it finds the minutes where
message volume spikes well above the recent baseline, then collapses nearby spikes so
only the single biggest peak in a burst is reported.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median

from stream_sniper.database.gateways.analytics.records import StreamBucketRow

WINDOW = 10
SPIKE_MULTIPLIER = 3.0
MIN_ABSOLUTE = 15
MIN_GAP_MINUTES = 5

TIMELINE_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


@dataclass(frozen=True)
class DetectedMoment:
    """Analytics-owned spike result, independent of transport models."""

    bucket_minute: str
    offset_seconds: int
    message_count: int
    baseline: float
    ratio: float | None
    unique_chatters: int


@dataclass(frozen=True)
class _MomentCandidate:
    minute: datetime
    count: int
    unique_chatters: int
    baseline: float


def _parse_buckets(buckets: Sequence[StreamBucketRow]) -> list[tuple[datetime, int, int]]:
    return [
        (datetime.strptime(row.bucket_minute, TIMELINE_DATETIME_FORMAT), row.message_count, row.unique_chatters)
        for row in buckets
    ]


def _zero_filled_series(
    parsed: Sequence[tuple[datetime, int, int]],
) -> tuple[list[datetime], list[int], list[int]]:
    bucket_map = {minute: (count, unique) for minute, count, unique in parsed}
    minutes: list[datetime] = []
    cursor = parsed[0][0]
    while cursor <= parsed[-1][0]:
        minutes.append(cursor)
        cursor += timedelta(minutes=1)
    return (
        minutes,
        [bucket_map.get(minute, (0, 0))[0] for minute in minutes],
        [bucket_map.get(minute, (0, 0))[1] for minute in minutes],
    )


def _find_candidates(
    minutes: Sequence[datetime],
    counts: Sequence[int],
    uniques: Sequence[int],
) -> list[_MomentCandidate]:
    candidates: list[_MomentCandidate] = []
    for index, minute in enumerate(minutes):
        window = counts[max(0, index - WINDOW) : index]
        baseline = float(median(window)) if window else 0.0
        if counts[index] >= max(SPIKE_MULTIPLIER * baseline, MIN_ABSOLUTE):
            candidates.append(_MomentCandidate(minute, counts[index], uniques[index], baseline))
    return candidates


def _collapse_candidates(
    candidates: Sequence[_MomentCandidate],
) -> list[_MomentCandidate]:
    kept: list[_MomentCandidate] = []
    group_peak: _MomentCandidate | None = None
    for candidate in candidates:
        starts_new_group = group_peak is None or candidate.minute - group_peak.minute >= timedelta(
            minutes=MIN_GAP_MINUTES
        )
        if starts_new_group:
            if group_peak is not None:
                kept.append(group_peak)
            group_peak = candidate
        elif group_peak is not None and candidate.count > group_peak.count:
            group_peak = candidate
    if group_peak is not None:
        kept.append(group_peak)
    return kept


def _as_detected_moment(candidate: _MomentCandidate, base: datetime) -> DetectedMoment:
    return DetectedMoment(
        bucket_minute=candidate.minute.strftime(TIMELINE_DATETIME_FORMAT),
        offset_seconds=int((candidate.minute - base).total_seconds()),
        message_count=candidate.count,
        baseline=candidate.baseline,
        ratio=(round(candidate.count / candidate.baseline, 2) if candidate.baseline > 0 else None),
        unique_chatters=candidate.unique_chatters,
    )


def detect_moments(buckets: Sequence[StreamBucketRow], stream_start: str | None) -> list[DetectedMoment]:
    """Detect spike moments in ``buckets``.

    ``buckets`` contains gateway records in ascending minute order. ``stream_start``
    is the stream's start ISO string used for ``offset_seconds``; when ``None`` the offset is
    measured from the first bucket. Returns moments ordered by ``bucket_minute`` ASC.
    """
    parsed = _parse_buckets(buckets)
    if not parsed:
        return []

    first_minute = parsed[0][0]
    base = datetime.strptime(stream_start, TIMELINE_DATETIME_FORMAT) if stream_start else first_minute
    minutes, counts, uniques = _zero_filled_series(parsed)
    candidates = _find_candidates(minutes, counts, uniques)
    return [_as_detected_moment(candidate, base) for candidate in _collapse_candidates(candidates)]
