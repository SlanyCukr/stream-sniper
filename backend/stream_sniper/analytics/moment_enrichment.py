"""Enrich detected spike moments with window-level context for persistence.

Runs after ``detect_moments`` over the per-minute buckets. For every moment it looks at the
window ``[bucket_minute - 1min, bucket_minute + 2min)`` and derives sub/emote share, the most
distinctive phrases (lift vs the whole stream), and a few representative repeated messages. All
window messages for every moment are fetched in ONE query and partitioned in memory — no
per-moment N+1.
"""

from collections import Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from ..database.message_table_gateway import select_moment_window_messages_db
from . import text_stats
from .moments import detect_moments

_FMT = "%Y-%m-%dT%H:%M:%S"

# Window around a spike minute: one minute before through two minutes after (half-open).
_WINDOW_BEFORE = timedelta(minutes=1)
_WINDOW_AFTER = timedelta(minutes=2)

_MAX_TOP_PHRASES = 5
_MAX_SAMPLE_MESSAGES = 3


def _stream_span_minutes(buckets) -> float:
    """Observed minutes between the first and last bucket (>= 1), for per-minute frequency."""
    if not buckets:
        return 1.0
    first = datetime.strptime(buckets[0][0], _FMT)
    last = datetime.strptime(buckets[-1][0], _FMT)
    return max((last - first).total_seconds() / 60.0 + 1.0, 1.0)


def enrich_moments(
    stream_id: int,
    buckets: List[Tuple],
    stream_start: Optional[str],
    phrase_usage: Dict[str, int],
    emote_names: Set[str],
) -> List[Tuple]:
    """Return persisted-moment rows for ``replace_stream_text_rollups_db``.

    Each row is ``(bucket_minute, offset_seconds, message_count, baseline, ratio, unique_chatters,
    sub_share, emote_share, top_phrases, sample_messages)`` where the last two are JSON-serializable
    lists (or None). ``phrase_usage`` is the whole-stream phrase occurrence map from
    ``text_stats.phrase_stats`` (used to compute per-minute frequency for lift).
    """
    moments = detect_moments(buckets, stream_start)
    if not moments:
        return []

    span_minutes = _stream_span_minutes(buckets)
    stream_freq = {phrase: count / span_minutes for phrase, count in phrase_usage.items()}

    windows: List[Tuple[datetime, datetime]] = []
    for moment in moments:
        center = datetime.strptime(moment.bucket_minute, _FMT)
        windows.append((center - _WINDOW_BEFORE, center + _WINDOW_AFTER))

    rows = select_moment_window_messages_db(stream_id, windows)

    # Partition messages into the windows they fall in (windows can overlap in principle).
    buckets_by_window: List[List[Tuple]] = [[] for _ in windows]
    for time, text, chatter_id, is_subscriber, emote_count in rows:
        for idx, (start, end) in enumerate(windows):
            if start <= time < end:
                buckets_by_window[idx].append((text, chatter_id, is_subscriber, emote_count))

    moment_rows: List[Tuple] = []
    for moment, window_messages in zip(moments, buckets_by_window, strict=True):
        total = len(window_messages)
        if total > 0:
            subs = sum(1 for _t, _c, is_sub, _e in window_messages if is_sub is True)
            emotes = sum(1 for _t, _c, _s, emote_count in window_messages if emote_count is not None)
            sub_share = round(subs / total, 4)
            emote_share = round(emotes / total, 4)
        else:
            sub_share = None
            emote_share = None

        window_rows = [(text, 1) for text, _c, _s, _e in window_messages]
        distinctive = text_stats.distinctive_phrases(
            window_rows, stream_freq, emote_names, limit=_MAX_TOP_PHRASES
        )
        top_phrases = [{"phrase": phrase, "count": count, "lift": lift} for phrase, count, lift in distinctive]

        text_counts = Counter(text for text, _c, _s, _e in window_messages if text)
        sample_messages = [
            {"text": text, "count": count} for text, count in text_counts.most_common(_MAX_SAMPLE_MESSAGES)
        ]

        moment_rows.append(
            (
                moment.bucket_minute,
                moment.offset_seconds,
                moment.message_count,
                moment.baseline,
                moment.ratio,
                moment.unique_chatters,
                sub_share,
                emote_share,
                top_phrases or None,
                sample_messages or None,
            )
        )

    return moment_rows
