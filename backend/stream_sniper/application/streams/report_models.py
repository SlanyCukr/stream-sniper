"""Canonical stream-report read models shared with the API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from stream_sniper.database.gateways.content.records import MomentReviewStatus

if TYPE_CHECKING:
    from stream_sniper.database.gateways.analytics.records import TopEmoteRow, TopPhraseRow
    from stream_sniper.database.gateways.content.records import StreamMomentRow


class ReportMetric(BaseModel):
    value: float | None = None
    delta_pct: float | None = None
    percentile: float | None = None
    baseline_median: float | None = None


class TopEmote(BaseModel):
    name: str
    source: str
    provider_id: str | None = None
    usage_count: int
    chatter_count: int

    @classmethod
    def from_row(cls, row: TopEmoteRow) -> TopEmote:
        return cls(
            name=row.name,
            source=row.source,
            provider_id=row.provider_id,
            usage_count=row.usage_count,
            chatter_count=row.chatter_count,
        )


class TopPhrase(BaseModel):
    phrase: str
    usage_count: int
    chatter_count: int

    @classmethod
    def from_row(cls, row: TopPhraseRow) -> TopPhrase:
        return cls(phrase=row.phrase, usage_count=row.usage_count, chatter_count=row.chatter_count)


class ReportMoment(BaseModel):
    bucket_minute: str
    offset_seconds: int
    message_count: int
    ratio: float | None = None
    status: MomentReviewStatus | None = None

    @classmethod
    def from_row(cls, row: StreamMomentRow) -> ReportMoment:
        return cls(
            bucket_minute=row.bucket_minute,
            offset_seconds=row.offset_seconds,
            message_count=row.message_count,
            ratio=row.ratio,
            status=row.status,
        )


class ReportMetrics(BaseModel):
    messages_per_minute: ReportMetric
    total_messages: ReportMetric
    unique_chatters: ReportMetric
    new_chatters: ReportMetric
    returning_chatters: ReportMetric
    sub_share: ReportMetric
    peak_messages: ReportMetric
    avg_viewers: ReportMetric
    peak_viewers: ReportMetric


class StreamReport(BaseModel):
    stream_id: int
    creator_id: int
    baseline_count: int
    lookback: int
    metrics: ReportMetrics
    creator_nick: str | None = None
    title: str | None = None
    start: str | None = None
    end: str | None = None
    duration_seconds: int | None = None
    peak_bucket_minute: str | None = None
    top_emote: TopEmote | None = None
    top_phrase: TopPhrase | None = None
    top_moments: list[ReportMoment] = Field(default_factory=list)
