"""Application query for the baseline-compared stream report read model."""

from datetime import datetime

from stream_sniper.database.core.wire_format import WIRE_TS_FORMAT
from stream_sniper.database.gateways.analytics.records import (
    CreatorReportRow,
    StreamMetricsRow,
)
from stream_sniper.database.gateways.analytics.stream_emote_stats_table_gateway import select_stream_emotes_db
from stream_sniper.database.gateways.analytics.stream_metrics_table_gateway import (
    select_creator_report_series_db,
    select_stream_metrics_db,
)
from stream_sniper.database.gateways.analytics.stream_phrase_stats_table_gateway import select_stream_phrases_db
from stream_sniper.database.gateways.content.records import StreamMomentRow
from stream_sniper.database.gateways.content.stream_moment_table_gateway import select_stream_moments_db
from stream_sniper.database.gateways.streams.records import peak_viewer_count
from stream_sniper.database.gateways.streams.stream_table_gateway import select_stream_comprehensive_db
from stream_sniper.database.gateways.streams.stream_viewer_sample_table_gateway import select_stream_viewer_samples_db

from ...analytics.calculations.report_stats import build_metric
from .report_models import (
    ReportMetric,
    ReportMetrics,
    ReportMoment,
    StreamReport,
    TopEmote,
    TopPhrase,
)


class StreamNotFoundError(LookupError):
    """Raised when the requested stream has no persistence row."""


def get_stream_report(stream_id: int, lookback: int) -> StreamReport:
    """Coordinate report gateways and construct the typed report read model."""
    comprehensive = select_stream_comprehensive_db(stream_id)
    if comprehensive is None:
        raise StreamNotFoundError(stream_id)

    creator_id = comprehensive.creator_id
    start = _iso(comprehensive.start)
    metrics_row = select_stream_metrics_db(stream_id)
    sample_rows = select_stream_viewer_samples_db(stream_id)
    emote_rows = select_stream_emotes_db(stream_id, 1)
    phrase_rows = select_stream_phrases_db(stream_id, 1)
    moment_rows = select_stream_moments_db(stream_id)
    series_rows = select_creator_report_series_db(creator_id, lookback + 1)
    baseline_rows = _previous_rows(series_rows, start, stream_id, lookback)
    survivors = [row for row in baseline_rows if row.total_messages is not None and row.messages_per_minute is not None]

    report_values = _report_values(metrics_row)
    viewer_counts = [row.viewer_count for row in sample_rows]
    avg_viewers = sum(viewer_counts) / len(viewer_counts) if viewer_counts else None
    peak_viewers = peak_viewer_count(sample_rows)

    return StreamReport(
        stream_id=stream_id,
        creator_id=creator_id,
        creator_nick=comprehensive.creator_nick,
        title=comprehensive.title,
        start=start,
        end=_iso(comprehensive.end),
        duration_seconds=report_values.duration_seconds,
        baseline_count=len(survivors),
        lookback=lookback,
        metrics=_build_metrics(report_values, survivors, avg_viewers, peak_viewers),
        peak_bucket_minute=report_values.peak_bucket_minute,
        top_emote=TopEmote.from_row(emote_rows[0]) if emote_rows else None,
        top_phrase=TopPhrase.from_row(phrase_rows[0]) if phrase_rows else None,
        top_moments=_top_moments(moment_rows),
    )


def _report_values(metrics: StreamMetricsRow | None) -> StreamMetricsRow:
    if metrics is not None:
        return metrics
    return StreamMetricsRow(*(None for _ in StreamMetricsRow._fields))


def _build_metrics(
    current: StreamMetricsRow,
    baseline: list[CreatorReportRow],
    avg_viewers: float | None,
    peak_viewers: int | None,
) -> ReportMetrics:
    def metric(value: float | int | None, values: list[float | int | None]) -> ReportMetric:
        return ReportMetric(**build_metric(value, values))

    return ReportMetrics(
        messages_per_minute=metric(current.messages_per_minute, [row.messages_per_minute for row in baseline]),
        total_messages=metric(current.total_messages, [row.total_messages for row in baseline]),
        unique_chatters=metric(current.unique_chatters, [row.unique_chatters for row in baseline]),
        new_chatters=metric(current.new_chatters, [row.new_chatters for row in baseline]),
        returning_chatters=metric(current.returning_chatters, [row.returning_chatters for row in baseline]),
        sub_share=metric(
            _sub_share(current.sub_messages, current.total_messages),
            [_sub_share(row.sub_messages, row.total_messages) for row in baseline],
        ),
        peak_messages=metric(current.peak_messages, [row.peak_messages for row in baseline]),
        avg_viewers=ReportMetric(value=avg_viewers),
        peak_viewers=ReportMetric(value=peak_viewers),
    )


def _iso(value: str | datetime | None) -> str | None:
    if value is None or isinstance(value, str):
        return value
    return value.strftime(WIRE_TS_FORMAT)


def _sub_share(sub_messages: int | None, total_messages: int | None) -> float | None:
    """Nullable share rounded to 4 places — same precision contract as compare's _share."""
    if sub_messages is None or total_messages is None or total_messages == 0:
        return None
    return round(sub_messages / total_messages, 4)


def _previous_rows(
    series_rows: list[CreatorReportRow],
    start: str | None,
    stream_id: int,
    lookback: int,
) -> list[CreatorReportRow]:
    if start is None:
        return []
    previous = [row for row in series_rows if row.start is not None and (row.start, row.stream_id) < (start, stream_id)]
    return previous[-lookback:]


def _top_moments(rows: list[StreamMomentRow]) -> list[ReportMoment]:
    accepted = [row for row in rows if row.status != "rejected"]
    ranked = sorted(accepted, key=lambda row: (row.ratio is not None, row.ratio or 0.0), reverse=True)
    return [ReportMoment.from_row(row) for row in ranked[:3]]
