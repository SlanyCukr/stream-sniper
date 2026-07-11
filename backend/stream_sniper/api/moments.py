"""Spike-moment detection over per-minute message buckets.

Pure, dependency-light function used by the timeline endpoint (§4.4). Given the
ascending per-minute buckets already fetched for a stream, it finds the minutes where
message volume spikes well above the recent baseline, then collapses nearby spikes so
only the single biggest peak in a burst is reported.
"""

from datetime import datetime, timedelta
from statistics import median
from typing import List, Optional

from .timeline_models import TimelineMoment

WINDOW = 10
SPIKE_MULTIPLIER = 3.0
MIN_ABSOLUTE = 15
MIN_GAP_MINUTES = 5

_FMT = "%Y-%m-%dT%H:%M:%S"


def detect_moments(buckets, stream_start: Optional[str]) -> List[TimelineMoment]:
    """Detect spike moments in ``buckets``.

    ``buckets`` is a list of ``(bucket_minute_iso, message_count, unique_chatters)`` tuples
    in ascending minute order (as returned by ``select_stream_buckets_db``). ``stream_start``
    is the stream's start ISO string used for ``offset_seconds``; when ``None`` the offset is
    measured from the first bucket. Returns moments ordered by ``bucket_minute`` ASC.
    """
    parsed = [(datetime.strptime(row[0], _FMT), int(row[1]), int(row[2])) for row in buckets]
    if not parsed:
        return []

    first_minute = parsed[0][0]
    last_minute = parsed[-1][0]
    base = datetime.strptime(stream_start, _FMT) if stream_start else first_minute

    # Zero-fill every missing minute between the first and last observed bucket.
    bucket_map = {minute: (count, unique) for minute, count, unique in parsed}
    minutes: List[datetime] = []
    cursor = first_minute
    while cursor <= last_minute:
        minutes.append(cursor)
        cursor += timedelta(minutes=1)
    counts = [bucket_map.get(minute, (0, 0))[0] for minute in minutes]
    uniques = [bucket_map.get(minute, (0, 0))[1] for minute in minutes]

    # Candidate minutes: count clears max(SPIKE_MULTIPLIER * median(window), MIN_ABSOLUTE).
    candidates = []
    for i, minute in enumerate(minutes):
        window = counts[max(0, i - WINDOW):i]
        baseline = float(median(window)) if window else 0.0
        threshold = max(SPIKE_MULTIPLIER * baseline, MIN_ABSOLUTE)
        if counts[i] >= threshold:
            candidates.append((minute, counts[i], uniques[i], baseline))

    # Collapse candidates within MIN_GAP_MINUTES of the current group's kept peak, keeping the
    # highest-count minute per group (ties -> earliest). A new group begins once a candidate is
    # >= MIN_GAP_MINUTES after that kept peak.
    kept = []
    group_peak = None
    for candidate in candidates:
        minute = candidate[0]
        if group_peak is None or (minute - group_peak[0]).total_seconds() / 60.0 >= MIN_GAP_MINUTES:
            if group_peak is not None:
                kept.append(group_peak)
            group_peak = candidate
        elif candidate[1] > group_peak[1]:
            group_peak = candidate
    if group_peak is not None:
        kept.append(group_peak)

    moments = []
    for minute, count, unique, baseline in kept:
        moments.append(
            TimelineMoment(
                bucket_minute=minute.strftime(_FMT),
                offset_seconds=int((minute - base).total_seconds()),
                message_count=count,
                baseline=baseline,
                ratio=round(count / baseline, 2) if baseline > 0 else None,
                unique_chatters=unique,
            )
        )
    return moments
