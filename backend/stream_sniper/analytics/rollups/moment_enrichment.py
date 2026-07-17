"""Enrich detected spike moments with window-level context for persistence.

Runs after ``detect_moments`` over the per-minute buckets. For every moment it looks at the
window ``[bucket_minute - 1min, bucket_minute + 2min)`` and derives sub/emote share, the most
distinctive phrases (lift vs the whole stream), and a few representative repeated messages. All
window messages for every moment are fetched in ONE query and partitioned in memory — no
per-moment N+1.
"""

from collections import Counter
from collections.abc import Sequence
from datetime import datetime, timedelta

from stream_sniper.database.core.wire_format import WIRE_TS_FORMAT
from stream_sniper.database.gateways.analytics.records import StreamBucketRow
from stream_sniper.database.gateways.chat.records import MomentWindowRow
from stream_sniper.database.gateways.content.records import (
    MomentWriteRow,
    SampleMessagePayload,
    TopPhrasePayload,
)

from ...database.gateways.chat.message_table_gateway import select_moment_window_messages_db
from ..calculations import text_stats
from ..calculations.moments import DetectedMoment, detect_moments

# Window around a spike minute: one minute before through two minutes after (half-open).
_WINDOW_BEFORE = timedelta(minutes=1)
_WINDOW_AFTER = timedelta(minutes=2)

_MAX_TOP_PHRASES = 5
_MAX_SAMPLE_MESSAGES = 3


def _stream_span_minutes(buckets: Sequence[StreamBucketRow]) -> float:
    """Observed minutes between the first and last bucket (>= 1), for per-minute frequency."""
    if not buckets:
        return 1.0
    first = datetime.strptime(buckets[0].bucket_minute, WIRE_TS_FORMAT)
    last = datetime.strptime(buckets[-1].bucket_minute, WIRE_TS_FORMAT)
    return max((last - first).total_seconds() / 60.0 + 1.0, 1.0)


def _partition_window_messages(
    rows: Sequence[MomentWindowRow], windows: Sequence[tuple[datetime, datetime]]
) -> list[list[MomentWindowRow]]:
    messages_by_window: list[list[MomentWindowRow]] = [[] for _ in windows]
    for row in rows:
        for index, (start, end) in enumerate(windows):
            if start <= row.sent_at < end:
                messages_by_window[index].append(row)
    return messages_by_window


def _build_enriched_moment_row(
    moment: DetectedMoment,
    window_messages: Sequence[MomentWindowRow],
    stream_frequency: dict[str, float],
    emote_names: set[str],
) -> MomentWriteRow:
    # Old rows can lack both subscriber and emote metadata. Use only known rows as
    # the denominator so an all-unknown window remains None instead of becoming zero.
    known = sum(1 for row in window_messages if row.is_subscriber is not None)
    if known > 0:
        subscribers = sum(1 for row in window_messages if row.is_subscriber is True)
        emotes = sum(1 for row in window_messages if row.emote_count and row.emote_count > 0)
        subscriber_share = round(subscribers / known, 4)
        emote_share = round(emotes / known, 4)
    else:
        subscriber_share = None
        emote_share = None

    window_rows = [(row.text, 1) for row in window_messages]
    distinctive = text_stats.distinctive_phrases(window_rows, stream_frequency, emote_names, limit=_MAX_TOP_PHRASES)
    top_phrases: list[TopPhrasePayload] = [
        {"phrase": phrase, "count": count, "lift": lift} for phrase, count, lift in distinctive
    ]
    text_counts = Counter(row.text for row in window_messages if row.text)
    sample_messages: list[SampleMessagePayload] = [
        {"text": text, "count": count} for text, count in text_counts.most_common(_MAX_SAMPLE_MESSAGES)
    ]
    return MomentWriteRow(
        moment.bucket_minute,
        moment.offset_seconds,
        moment.message_count,
        moment.baseline,
        moment.ratio,
        moment.unique_chatters,
        subscriber_share,
        emote_share,
        top_phrases or None,
        sample_messages or None,
    )


def enrich_moments(
    stream_id: int,
    buckets: Sequence[StreamBucketRow],
    stream_start: str | None,
    phrase_usage: dict[str, int],
    emote_names: set[str],
) -> list[MomentWriteRow]:
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

    windows: list[tuple[datetime, datetime]] = []
    for moment in moments:
        center = datetime.strptime(moment.bucket_minute, WIRE_TS_FORMAT)
        windows.append((center - _WINDOW_BEFORE, center + _WINDOW_AFTER))

    messages_by_window = _partition_window_messages(select_moment_window_messages_db(stream_id, windows), windows)
    return [
        _build_enriched_moment_row(moment, messages, stream_freq, emote_names)
        for moment, messages in zip(moments, messages_by_window, strict=True)
    ]
