"""Pydantic contracts for the stream report card endpoint (snake_case wire format)."""

from typing import List, Optional

from pydantic import BaseModel


class ReportMetric(BaseModel):
    # None = unknown (stream not rolled up yet, or fewer than 2 rolled-up baseline
    # streams) — never coalesced to 0 (the nullable=unknown contract).
    value: Optional[float] = None
    delta_pct: Optional[float] = None
    percentile: Optional[float] = None
    baseline_median: Optional[float] = None


class TopEmote(BaseModel):
    name: str
    source: str
    provider_id: Optional[str] = None
    usage_count: int
    chatter_count: int


class TopPhrase(BaseModel):
    phrase: str
    usage_count: int
    chatter_count: int


class ReportMoment(BaseModel):
    bucket_minute: str
    offset_seconds: int
    message_count: int
    ratio: Optional[float] = None
    # moment_review status ('bookmarked'; 'rejected' moments are excluded); None = pending.
    status: Optional[str] = None


class ReportMetrics(BaseModel):
    messages_per_minute: ReportMetric
    total_messages: ReportMetric
    unique_chatters: ReportMetric
    new_chatters: ReportMetric
    returning_chatters: ReportMetric
    sub_share: ReportMetric
    peak_messages: ReportMetric
    # Viewer metrics carry a value only — historical viewer matching is out of scope,
    # so delta_pct/percentile/baseline_median stay None.
    avg_viewers: ReportMetric
    peak_viewers: ReportMetric


class StreamReport(BaseModel):
    stream_id: int
    creator_id: int
    creator_nick: Optional[str] = None
    title: Optional[str] = None
    start: Optional[str] = None
    end: Optional[str] = None
    duration_seconds: Optional[int] = None
    # Previous rolled-up streams that actually entered the baseline math (<= lookback).
    baseline_count: int
    lookback: int
    metrics: ReportMetrics
    peak_bucket_minute: Optional[str] = None
    top_emote: Optional[TopEmote] = None
    top_phrase: Optional[TopPhrase] = None
    top_moments: List[ReportMoment] = []
