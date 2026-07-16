"""Application query for per-stream timeline analytics."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from stream_sniper.database.gateways.analytics.records import (
    StreamBucketRow,
    StreamHeaderRow,
    StreamMetricsRow,
)
from stream_sniper.database.gateways.content.records import StreamMomentRow
from stream_sniper.database.gateways.streams.records import (
    StreamContextChangeRow,
    ViewerSampleRow,
)

from ...analytics.calculations.moments import DetectedMoment, detect_moments
from .timeline_models import (
    StreamContextChange,
    StreamTimeline,
    TimelineBucket,
    TimelineMetrics,
    TimelineMoment,
    ViewerSample,
)

_FMT = "%Y-%m-%dT%H:%M:%S"


@dataclass(frozen=True)
class StreamTimelineSources:
    """Persistence dependencies for building a stream timeline."""

    select_buckets: Callable[[int], list[StreamBucketRow]]
    select_metrics: Callable[[int], StreamMetricsRow | None]
    select_header: Callable[[int], StreamHeaderRow | None]
    select_moments: Callable[[int], list[StreamMomentRow]]
    select_viewer_samples: Callable[[int], list[ViewerSampleRow]]
    select_context_changes: Callable[[int], list[StreamContextChangeRow]]


def get_stream_timeline(stream_id: int, sources: StreamTimelineSources) -> StreamTimeline:
    """Coordinate timeline gateways and construct the typed timeline read model."""
    bucket_rows = sources.select_buckets(stream_id)
    metrics_row = sources.select_metrics(stream_id)
    header_row = sources.select_header(stream_id)
    moment_rows = sources.select_moments(stream_id)
    sample_rows = sources.select_viewer_samples(stream_id)
    context_rows = sources.select_context_changes(stream_id)

    stream_start = header_row.start if header_row else None
    twitch_vod_id = header_row.twitch_vod_id if header_row else None
    viewer_samples = [ViewerSample(t=row.sampled_at, viewer_count=row.viewer_count) for row in sample_rows]
    moments = (
        _persisted_moments(moment_rows) if moment_rows else _detected_moments(detect_moments(bucket_rows, stream_start))
    )
    return StreamTimeline(
        stream_id=stream_id,
        stream_start=stream_start,
        twitch_vod_id=twitch_vod_id,
        buckets=_zero_filled_buckets(bucket_rows),
        moments=moments,
        metrics=_metrics(metrics_row),
        viewer_samples=viewer_samples,
        peak_viewers=max((sample.viewer_count for sample in viewer_samples), default=None),
        context_changes=_context_changes(context_rows),
    )


def _zero_filled_buckets(rows: list[StreamBucketRow]) -> list[TimelineBucket]:
    if not rows:
        return []
    observed = {
        row.bucket_minute: TimelineBucket(
            bucket_minute=row.bucket_minute,
            message_count=row.message_count,
            unique_chatters=row.unique_chatters,
            sub_messages=row.sub_messages,
            emote_messages=row.emote_messages,
        )
        for row in rows
    }
    first = datetime.strptime(rows[0].bucket_minute, _FMT)
    last = datetime.strptime(rows[-1].bucket_minute, _FMT)
    result: list[TimelineBucket] = []
    cursor = first
    while cursor <= last:
        key = cursor.strftime(_FMT)
        result.append(
            observed.get(
                key,
                TimelineBucket(bucket_minute=key, message_count=0, unique_chatters=0),
            )
        )
        cursor += timedelta(minutes=1)
    return result


def _persisted_moments(rows: list[StreamMomentRow]) -> list[TimelineMoment]:
    return [
        TimelineMoment(
            bucket_minute=row.bucket_minute,
            offset_seconds=row.offset_seconds,
            message_count=row.message_count,
            baseline=row.baseline,
            ratio=row.ratio,
            unique_chatters=row.unique_chatters,
            sub_share=row.sub_share,
            emote_share=row.emote_share,
            top_phrases=row.top_phrases,
            sample_messages=row.sample_messages,
            status=row.status,
            persisted=True,
        )
        for row in rows
    ]


def _detected_moments(rows: list[DetectedMoment]) -> list[TimelineMoment]:
    return [
        TimelineMoment(
            bucket_minute=row.bucket_minute,
            offset_seconds=row.offset_seconds,
            message_count=row.message_count,
            baseline=row.baseline,
            ratio=row.ratio,
            unique_chatters=row.unique_chatters,
        )
        for row in rows
    ]


def _metrics(row: StreamMetricsRow | None) -> TimelineMetrics | None:
    if row is None:
        return None
    return TimelineMetrics(
        total_messages=row.total_messages or 0,
        unique_chatters=row.unique_chatters or 0,
        duration_seconds=row.duration_seconds,
        messages_per_minute=row.messages_per_minute,
        peak_messages=row.peak_messages or 0,
        peak_bucket_minute=row.peak_bucket_minute,
        new_chatters=row.new_chatters or 0,
        returning_chatters=row.returning_chatters or 0,
        sub_messages=row.sub_messages,
        emote_messages=row.emote_messages,
    )


def _context_changes(rows: list[StreamContextChangeRow]) -> list[StreamContextChange]:
    return [
        StreamContextChange(
            t=row.sampled_at,
            title=row.title,
            category_id=row.category_id,
            category_name=row.category_name,
            language=row.language,
            tags=row.tags or [],
            is_mature=row.is_mature,
        )
        for row in rows
    ]
