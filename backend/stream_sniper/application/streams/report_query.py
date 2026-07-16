"""Application query for the baseline-compared stream report read model."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from stream_sniper.database.gateways.analytics.records import (
    CreatorReportRow,
    StreamMetricsRow,
    TopEmoteRow,
    TopPhraseRow,
)
from stream_sniper.database.gateways.content.records import StreamMomentRow
from stream_sniper.database.gateways.streams.records import (
    StreamComprehensiveRow,
    ViewerSampleRow,
)

from ...analytics.calculations.report_stats import build_metric
from .report_models import (
    ReportMetric,
    ReportMetrics,
    ReportMoment,
    StreamReport,
    TopEmote,
    TopPhrase,
)

_ISO_FMT = "%Y-%m-%dT%H:%M:%S"


class StreamNotFoundError(LookupError):
    """Raised when the requested stream has no persistence row."""


@dataclass(frozen=True)
class StreamReportSources:
    """Persistence dependencies for building a stream report."""

    select_comprehensive: Callable[[int], StreamComprehensiveRow | None]
    select_metrics: Callable[[int], StreamMetricsRow | None]
    select_viewer_samples: Callable[[int], list[ViewerSampleRow]]
    select_emotes: Callable[[int, int], list[TopEmoteRow]]
    select_phrases: Callable[[int, int], list[TopPhraseRow]]
    select_moments: Callable[[int], list[StreamMomentRow]]
    select_creator_series: Callable[[int, int], list[CreatorReportRow]]


def get_stream_report(stream_id: int, lookback: int, sources: StreamReportSources) -> StreamReport:
    """Coordinate report gateways and construct the typed report read model."""
    comprehensive = sources.select_comprehensive(stream_id)
    if comprehensive is None:
        raise StreamNotFoundError(stream_id)

    creator_id = comprehensive.creator_id
    start = _iso(comprehensive.start)
    metrics_row = sources.select_metrics(stream_id)
    sample_rows = sources.select_viewer_samples(stream_id)
    emote_rows = sources.select_emotes(stream_id, 1)
    phrase_rows = sources.select_phrases(stream_id, 1)
    moment_rows = sources.select_moments(stream_id)
    series_rows = sources.select_creator_series(creator_id, lookback + 1)
    baseline_rows = _previous_rows(series_rows, start, stream_id, lookback)
    survivors = [row for row in baseline_rows if row.total_messages is not None and row.messages_per_minute is not None]

    report_values = _report_values(metrics_row)
    viewer_counts = [row.viewer_count for row in sample_rows]
    avg_viewers = sum(viewer_counts) / len(viewer_counts) if viewer_counts else None
    peak_viewers = max(viewer_counts) if viewer_counts else None

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
        top_emote=_top_emote(emote_rows),
        top_phrase=_top_phrase(phrase_rows),
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
    return value.strftime(_ISO_FMT)


def _sub_share(sub_messages: int | None, total_messages: int | None) -> float | None:
    if sub_messages is None or total_messages is None or total_messages == 0:
        return None
    return sub_messages / total_messages


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


def _top_emote(rows: list[TopEmoteRow]) -> TopEmote | None:
    if not rows:
        return None
    row = rows[0]
    return TopEmote(
        name=row.name,
        source=row.source,
        provider_id=row.provider_id,
        usage_count=row.usage_count,
        chatter_count=row.chatter_count,
    )


def _top_phrase(rows: list[TopPhraseRow]) -> TopPhrase | None:
    if not rows:
        return None
    row = rows[0]
    return TopPhrase(phrase=row.phrase, usage_count=row.usage_count, chatter_count=row.chatter_count)


def _top_moments(rows: list[StreamMomentRow]) -> list[ReportMoment]:
    accepted = [row for row in rows if row.status != "rejected"]
    ranked = sorted(accepted, key=lambda row: (row.ratio is not None, row.ratio or 0.0), reverse=True)
    return [
        ReportMoment(
            bucket_minute=row.bucket_minute,
            offset_seconds=row.offset_seconds,
            message_count=row.message_count,
            ratio=row.ratio,
            status=row.status,
        )
        for row in ranked[:3]
    ]
