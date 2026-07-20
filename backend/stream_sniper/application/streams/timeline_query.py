"""Application query for per-stream timeline analytics."""

from datetime import datetime, timedelta

from stream_sniper.database.core.wire_format import WIRE_TS_FORMAT
from stream_sniper.database.gateways.analytics.records import StreamBucketRow
from stream_sniper.database.gateways.analytics.stream_metrics_table_gateway import (
    select_stream_header_db,
    select_stream_metrics_db,
)
from stream_sniper.database.gateways.analytics.stream_time_bucket_table_gateway import select_stream_buckets_db
from stream_sniper.database.gateways.content.stream_moment_table_gateway import select_stream_moments_db
from stream_sniper.database.gateways.streams.records import peak_viewer_count
from stream_sniper.database.gateways.streams.stream_context_table_gateway import select_stream_context_changes_db
from stream_sniper.database.gateways.streams.stream_viewer_sample_table_gateway import select_stream_viewer_samples_db

from ...analytics.calculations.moments import detect_moments
from .timeline_models import (
    StreamContextChange,
    StreamTimeline,
    TimelineBucket,
    TimelineMetrics,
    TimelineMoment,
    ViewerSample,
)


def get_stream_timeline(stream_id: int) -> StreamTimeline:
    """Coordinate timeline gateways and construct the typed timeline read model."""
    bucket_rows = select_stream_buckets_db(stream_id)
    metrics_row = select_stream_metrics_db(stream_id)
    header_row = select_stream_header_db(stream_id)
    moment_rows = select_stream_moments_db(stream_id)
    sample_rows = select_stream_viewer_samples_db(stream_id)
    context_rows = select_stream_context_changes_db(stream_id)

    stream_start = header_row.start if header_row else None
    twitch_vod_id = header_row.twitch_vod_id if header_row else None
    viewer_samples = [ViewerSample(t=row.sampled_at, viewer_count=row.viewer_count) for row in sample_rows]
    moments = (
        [TimelineMoment.from_row(row) for row in moment_rows]
        if moment_rows
        else [TimelineMoment.from_detected(moment) for moment in detect_moments(bucket_rows, stream_start)]
    )
    return StreamTimeline(
        stream_id=stream_id,
        stream_start=stream_start,
        twitch_vod_id=twitch_vod_id,
        buckets=_zero_filled_buckets(bucket_rows),
        moments=moments,
        metrics=TimelineMetrics.from_row(metrics_row) if metrics_row is not None else None,
        viewer_samples=viewer_samples,
        peak_viewers=peak_viewer_count(sample_rows),
        context_changes=[StreamContextChange.from_row(row) for row in context_rows],
    )


def _zero_filled_buckets(rows: list[StreamBucketRow]) -> list[TimelineBucket]:
    if not rows:
        return []
    observed = {row.bucket_minute: TimelineBucket.from_row(row) for row in rows}
    first = datetime.strptime(rows[0].bucket_minute, WIRE_TS_FORMAT)
    last = datetime.strptime(rows[-1].bucket_minute, WIRE_TS_FORMAT)
    result: list[TimelineBucket] = []
    cursor = first
    while cursor <= last:
        key = cursor.strftime(WIRE_TS_FORMAT)
        result.append(
            observed.get(
                key,
                TimelineBucket(bucket_minute=key, message_count=0, unique_chatters=0),
            )
        )
        cursor += timedelta(minutes=1)
    return result
