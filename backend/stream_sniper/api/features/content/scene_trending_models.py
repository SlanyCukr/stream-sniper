"""Response contracts for the scene-wide trending (velocity) endpoints.

Trend classification and delta_pct are derived here from the gateway's current/prior
usage sums, keeping that policy in one place beside the response shape.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from ....analytics.calculations.delta import DeltaTrend, classify_delta, percent_change
from ....database.gateways.analytics.scene_trends_gateway import (
    TrendingCopypastaRow,
    TrendingEmoteRow,
)

# Map the shared trend decision onto this endpoint's wire vocabulary; the math and
# edge cases live in analytics.calculations.delta so the API and digest cannot drift.
_TREND_LABELS = {
    DeltaTrend.NO_CHANGE: "steady",
    DeltaTrend.NEW: "new",
    DeltaTrend.RISING: "rising",
    DeltaTrend.FALLING: "falling",
}


def _classify_trend(current: int, prior: int) -> str:
    """Bucket an entity by how its current-window usage moved against the prior window.

    "new" wins when there was prior usage of 0 but current growth; otherwise
    rising/falling/steady by comparison. (Current usage is always > 0 here — the
    gateway's floor guarantees it — so a zero prior always means "new".)
    """
    return _TREND_LABELS[classify_delta(current, prior)]


def _delta_pct(current: int, prior: int) -> float | None:
    """Percent change from prior to current (1 dp), or None when there is no prior baseline."""
    return percent_change(current, prior, digits=1)


class TrendingCopypasta(BaseModel):
    message_text_id: int
    text: str
    current_usage: int = Field(..., description="Total usage in the current window [now-window, now)")
    prior_usage: int = Field(..., description="Total usage in the prior window [now-2*window, now-window)")
    delta_pct: float | None = Field(None, description="Percent change vs the prior window; null when prior_usage is 0")
    trend: str = Field(..., description="One of: new, rising, falling, steady")
    stream_count: int = Field(..., description="Distinct streams in the current window")
    creator_count: int = Field(..., description="Distinct creators in the current window")
    first_seen: str | None = Field(None, description="Earliest send time in the current window (ISO 8601), if known")

    @classmethod
    def from_row(cls, row: TrendingCopypastaRow) -> TrendingCopypasta:
        return cls(
            message_text_id=row.message_text_id,
            text=row.text,
            current_usage=row.current_usage,
            prior_usage=row.prior_usage,
            delta_pct=_delta_pct(row.current_usage, row.prior_usage),
            trend=_classify_trend(row.current_usage, row.prior_usage),
            stream_count=row.stream_count,
            creator_count=row.creator_count,
            first_seen=row.first_seen,
        )


class TrendingCopypastas(BaseModel):
    window: int
    items: list[TrendingCopypasta]


class TrendingEmote(BaseModel):
    emote_id: int
    name: str
    source: str = Field(..., description="Emote provider: bttv or twitch")
    provider_id: str | None = None
    current_usage: int = Field(..., description="Total usage in the current window [now-window, now)")
    prior_usage: int = Field(..., description="Total usage in the prior window [now-2*window, now-window)")
    delta_pct: float | None = Field(None, description="Percent change vs the prior window; null when prior_usage is 0")
    trend: str = Field(..., description="One of: new, rising, falling, steady")
    chatter_reach: int = Field(..., description="Sum of per-stream chatter_count in the current window")
    creator_count: int = Field(..., description="Distinct channels the emote appeared in during the current window")
    first_seen: str | None = Field(None, description="Dictionary first-seen time (ISO 8601), if known")

    @classmethod
    def from_row(cls, row: TrendingEmoteRow) -> TrendingEmote:
        return cls(
            emote_id=row.emote_id,
            name=row.name,
            source=row.source,
            provider_id=row.provider_id,
            current_usage=row.current_usage,
            prior_usage=row.prior_usage,
            delta_pct=_delta_pct(row.current_usage, row.prior_usage),
            trend=_classify_trend(row.current_usage, row.prior_usage),
            chatter_reach=row.chatter_reach,
            creator_count=row.creator_count,
            first_seen=row.first_seen,
        )


class TrendingEmotes(BaseModel):
    window: int
    items: list[TrendingEmote]
