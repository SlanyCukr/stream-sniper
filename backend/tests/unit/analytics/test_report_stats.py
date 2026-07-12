"""Unit tests for the pure report-card baseline math (analytics/report_stats.py)."""

from stream_sniper.analytics.report_stats import (
    build_metric,
    delta_pct,
    median,
    percentile_rank,
)


class TestMedian:
    def test_empty_list_is_none(self):
        assert median([]) is None

    def test_single_value(self):
        assert median([7.0]) == 7.0

    def test_odd_count_returns_middle(self):
        assert median([9.0, 1.0, 5.0]) == 5.0

    def test_even_count_averages_middle_pair(self):
        assert median([1.0, 2.0, 3.0, 10.0]) == 2.5

    def test_returns_float_for_int_inputs(self):
        result = median([3, 1, 2])
        assert result == 2.0
        assert isinstance(result, float)


class TestPercentileRank:
    def test_value_above_all_is_100(self):
        assert percentile_rank([1.0, 2.0, 3.0], 10.0) == 100.0

    def test_value_below_all_is_0(self):
        assert percentile_rank([1.0, 2.0, 3.0], 0.5) == 0.0

    def test_midrank_counts_half_of_ties(self):
        # below=1, ties=2 -> (1 + 1) / 4 * 100
        assert percentile_rank([1.0, 2.0, 2.0, 3.0], 2.0) == 50.0

    def test_rounded_to_one_decimal(self):
        # below=2, ties=1 -> (2 + 0.5) / 3 * 100 = 83.33...
        assert percentile_rank([1.0, 2.0, 3.0], 3.0) == 83.3


class TestDeltaPct:
    def test_zero_median_is_none(self):
        assert delta_pct(5.0, 0.0) is None

    def test_increase(self):
        assert delta_pct(15.0, 10.0) == 50.0

    def test_decrease_is_negative(self):
        assert delta_pct(5.0, 10.0) == -50.0

    def test_rounded_to_one_decimal(self):
        assert delta_pct(10.0, 3.0) == 233.3


class TestBuildMetric:
    def test_full_shape_with_baseline(self):
        metric = build_metric(30.0, [10.0, 20.0])
        assert metric == {
            "value": 30.0,
            "delta_pct": 100.0,
            "percentile": 100.0,
            "baseline_median": 15.0,
        }

    def test_none_baseline_entries_dropped(self):
        metric = build_metric(30.0, [10.0, None, 20.0, None])
        assert metric["baseline_median"] == 15.0
        assert metric["delta_pct"] == 100.0
        assert metric["percentile"] == 100.0

    def test_fewer_than_two_known_baseline_values_guards(self):
        metric = build_metric(5.0, [10.0, None])
        assert metric == {
            "value": 5.0,
            "delta_pct": None,
            "percentile": None,
            "baseline_median": None,
        }

    def test_empty_baseline_keeps_value_only(self):
        assert build_metric(5.0, []) == {
            "value": 5.0,
            "delta_pct": None,
            "percentile": None,
            "baseline_median": None,
        }

    def test_none_value_keeps_baseline_median_only(self):
        metric = build_metric(None, [1.0, 2.0, 3.0])
        assert metric == {
            "value": None,
            "delta_pct": None,
            "percentile": None,
            "baseline_median": 2.0,
        }

    def test_all_none_everywhere(self):
        assert build_metric(None, [None, None]) == {
            "value": None,
            "delta_pct": None,
            "percentile": None,
            "baseline_median": None,
        }

    def test_baseline_median_rounded_to_two_decimals(self):
        metric = build_metric(3.0, [1.111, 2.222, 3.333])
        assert metric["baseline_median"] == 2.22

    def test_zero_median_gives_none_delta_but_percentile(self):
        metric = build_metric(5.0, [0.0, 0.0, 0.0])
        assert metric["delta_pct"] is None
        assert metric["percentile"] == 100.0
        assert metric["baseline_median"] == 0.0

    def test_value_coerced_to_float(self):
        metric = build_metric(1200, [1000, 1100])
        assert metric["value"] == 1200.0
        assert isinstance(metric["value"], float)
