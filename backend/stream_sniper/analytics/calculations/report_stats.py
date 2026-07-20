"""Pure baseline/percentile math for the stream report card (no DB, no FastAPI).

Operates on plain sequences so it unit-tests hermetically. The nullable=unknown
contract applies throughout: ``None`` inputs mean "not yet computed", never 0.
"""

import statistics
from typing import TypedDict


class ReportMetricValues(TypedDict):
    value: float | None
    delta_pct: float | None
    percentile: float | None
    baseline_median: float | None


def median(values: list[float]) -> float | None:
    """Median of a plain list of numbers; None for an empty list."""
    return float(statistics.median(values)) if values else None


def percentile_rank(baseline: list[float], value: float) -> float:
    """Mid-rank percentile of ``value`` within ``baseline`` (0..100, 1 decimal).

    Fraction of baseline entries strictly below the value, plus half of the ties.
    """
    below = sum(1 for entry in baseline if entry < value)
    ties = sum(1 for entry in baseline if entry == value)
    return round((below + ties / 2.0) / len(baseline) * 100, 1)


def delta_pct(value: float, baseline_median: float) -> float | None:
    """Percent change of ``value`` vs the baseline median (1 decimal); None when median is 0."""
    if baseline_median == 0:
        return None
    return round((value - baseline_median) / baseline_median * 100, 1)


def build_metric(value: float | None, baseline: list[float | None]) -> ReportMetricValues:
    """Build the ReportMetric dict shape for one metric.

    ``None`` baseline entries (unknown for that past stream) are dropped; baseline
    stats require at least 2 known baseline values, otherwise delta_pct, percentile
    and baseline_median are all None. A None ``value`` keeps baseline_median but
    yields no delta/percentile (nothing to compare).
    """
    clean = [float(entry) for entry in baseline if entry is not None]
    metric: ReportMetricValues = {
        "value": None if value is None else float(value),
        "delta_pct": None,
        "percentile": None,
        "baseline_median": None,
    }
    if len(clean) < 2:
        return metric

    # clean is non-empty here (len >= 2), so the median is a real number.
    baseline_med = float(statistics.median(clean))
    metric["baseline_median"] = round(baseline_med, 2)
    if value is None:
        return metric

    metric["delta_pct"] = delta_pct(float(value), baseline_med)
    metric["percentile"] = percentile_rank(clean, float(value))
    return metric
