"""Contracts for the stream comparison lab."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from stream_sniper.database.gateways.analytics.records import (
        StreamCompareHeaderRow,
        StreamPairRetentionRow,
    )


def _share(part: int | None, total: int | None) -> float | None:
    if part is None or total is None or total == 0:
        return None
    return round(part / total, 4)


class CompareCurvePoint(BaseModel):
    percent: int
    message_count: int
    unique_chatters: int


class ComparedStream(BaseModel):
    stream_id: int
    creator_id: int
    creator_nick: str
    creator_display_name: str
    title: str
    start: str | None = None
    duration_seconds: int | None = None
    total_messages: int | None = None
    messages_per_minute: float | None = None
    unique_chatters: int | None = None
    new_chatters: int | None = None
    returning_chatters: int | None = None
    sub_share: float | None = None
    emote_share: float | None = None
    peak_messages: int | None = None
    peak_bucket_minute: str | None = None
    peak_viewers: int | None = None
    curve: list[CompareCurvePoint]

    @classmethod
    def from_row(
        cls,
        row: StreamCompareHeaderRow,
        *,
        peak_viewers: int | None,
        curve: list[CompareCurvePoint],
    ) -> ComparedStream:
        return cls(
            stream_id=row.stream_id,
            creator_id=row.creator_id,
            creator_nick=row.creator_nick,
            creator_display_name=row.creator_display_name,
            title=row.title,
            start=row.start,
            duration_seconds=row.duration_seconds,
            total_messages=row.total_messages,
            messages_per_minute=row.messages_per_minute,
            unique_chatters=row.unique_chatters,
            new_chatters=row.new_chatters,
            returning_chatters=row.returning_chatters,
            sub_share=_share(row.sub_messages, row.total_messages),
            emote_share=_share(row.emote_messages, row.total_messages),
            peak_messages=row.peak_messages,
            peak_bucket_minute=row.peak_bucket_minute,
            peak_viewers=peak_viewers,
            curve=curve,
        )


class PairRetention(BaseModel):
    from_stream_id: int
    to_stream_id: int
    from_audience: int
    to_audience: int
    retained: int
    retention_rate: float | None = None

    @classmethod
    def from_row(cls, row: StreamPairRetentionRow) -> PairRetention:
        return cls(
            from_stream_id=row.from_stream_id,
            to_stream_id=row.to_stream_id,
            from_audience=row.from_audience,
            to_audience=row.to_audience,
            retained=row.retained,
            retention_rate=round(row.retained / row.from_audience, 4) if row.from_audience else None,
        )


class StreamComparison(BaseModel):
    streams: list[ComparedStream]
    retention: list[PairRetention]
