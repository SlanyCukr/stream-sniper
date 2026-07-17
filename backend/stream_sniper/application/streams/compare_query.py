"""Cross-gateway stream comparison assembly."""

from collections import defaultdict
from collections.abc import Sequence
from datetime import datetime

from stream_sniper.database.gateways.analytics.records import StreamCompareBucketRow
from stream_sniper.database.gateways.analytics.stream_compare_table_gateway import (
    select_stream_compare_buckets_db,
    select_stream_compare_headers_db,
    select_stream_pair_retention_db,
)
from stream_sniper.database.gateways.streams.stream_viewer_sample_table_gateway import select_stream_viewer_samples_db

from .compare_models import CompareCurvePoint, ComparedStream, PairRetention, StreamComparison

_TIMELINE_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%S"


class StreamComparisonNotFoundError(LookupError):
    """Raised when any requested stream is missing."""


def _share(part: int | None, total: int | None) -> float | None:
    if part is None or total is None or total == 0:
        return None
    return round(part / total, 4)


def normalize_curve(
    rows: Sequence[StreamCompareBucketRow], start: str | None, duration: int | None
) -> list[CompareCurvePoint]:
    """Collapse an arbitrary stream timeline into at most 101 percentage slots."""
    if not rows:
        return []
    start_dt = datetime.strptime(start, _TIMELINE_DATETIME_FORMAT) if start else None
    result: dict[int, list[int]] = {}
    for index, row in enumerate(rows):
        if start_dt is not None and duration and duration > 0:
            elapsed = (datetime.strptime(row.bucket_minute, _TIMELINE_DATETIME_FORMAT) - start_dt).total_seconds()
            percent = min(100, max(0, round(elapsed * 100 / duration)))
        else:
            percent = round(index * 100 / max(1, len(rows) - 1))
        existing = result.setdefault(percent, [0, 0])
        existing[0] += row.message_count
        existing[1] = max(existing[1], row.unique_chatters)
    return [
        CompareCurvePoint(percent=percent, message_count=values[0], unique_chatters=values[1])
        for percent, values in sorted(result.items())
    ]


def get_stream_comparison(stream_ids: list[int]) -> StreamComparison:
    headers = select_stream_compare_headers_db(stream_ids)
    if len(headers) != len(stream_ids):
        raise StreamComparisonNotFoundError
    header_by_id = {row.stream_id: row for row in headers}
    bucket_map: defaultdict[int, list[StreamCompareBucketRow]] = defaultdict(list)
    for row in select_stream_compare_buckets_db(stream_ids):
        bucket_map[row.stream_id].append(row)

    streams: list[ComparedStream] = []
    for stream_id in stream_ids:
        header = header_by_id[stream_id]
        samples = select_stream_viewer_samples_db(stream_id)
        streams.append(
            ComparedStream(
                stream_id=header.stream_id,
                creator_id=header.creator_id,
                creator_nick=header.creator_nick,
                creator_display_name=header.creator_display_name,
                title=header.title,
                start=header.start,
                duration_seconds=header.duration_seconds,
                total_messages=header.total_messages,
                messages_per_minute=header.messages_per_minute,
                unique_chatters=header.unique_chatters,
                new_chatters=header.new_chatters,
                returning_chatters=header.returning_chatters,
                sub_share=_share(header.sub_messages, header.total_messages),
                emote_share=_share(header.emote_messages, header.total_messages),
                peak_messages=header.peak_messages,
                peak_bucket_minute=header.peak_bucket_minute,
                peak_viewers=max((sample.viewer_count for sample in samples), default=None),
                curve=normalize_curve(bucket_map[stream_id], header.start, header.duration_seconds),
            )
        )

    retention = [
        PairRetention(
            from_stream_id=row.from_stream_id,
            to_stream_id=row.to_stream_id,
            from_audience=row.from_audience,
            to_audience=row.to_audience,
            retained=row.retained,
            retention_rate=round(row.retained / row.from_audience, 4) if row.from_audience else None,
        )
        for row in select_stream_pair_retention_db(stream_ids)
    ]
    return StreamComparison(streams=streams, retention=retention)
