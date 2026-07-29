"""The shared percent-change-vs-prior policy and its three callers' presentation."""

from stream_sniper.analytics.calculations.delta import DeltaTrend, classify_delta, percent_change
from stream_sniper.analytics.operations.digest import _delta_label


class TestClassifyDelta:
    def test_all_zero_is_no_change_not_new(self):
        # The unified edge case: prior==0 AND current==0 means "hasn't moved", not "new".
        assert classify_delta(0, 0) is DeltaTrend.NO_CHANGE

    def test_zero_prior_with_growth_is_new(self):
        assert classify_delta(5, 0) is DeltaTrend.NEW

    def test_equal_nonzero_is_no_change(self):
        assert classify_delta(8, 8) is DeltaTrend.NO_CHANGE

    def test_rising_and_falling(self):
        assert classify_delta(10, 5) is DeltaTrend.RISING
        assert classify_delta(5, 10) is DeltaTrend.FALLING


class TestPercentChange:
    def test_none_when_no_baseline(self):
        assert percent_change(5, 0) is None
        assert percent_change(0, 0) is None

    def test_signed_one_decimal_default(self):
        assert percent_change(15, 10) == 50.0
        assert percent_change(5, 10) == -50.0
        assert percent_change(10, 3) == 233.3

    def test_equal_is_exactly_zero(self):
        assert percent_change(8, 8) == 0.0

    def test_whole_number_variant_returns_int(self):
        # digits=None rounds to a whole number and returns an int (digest presentation).
        pct = percent_change(340, 120, digits=None)
        assert pct == 183
        assert isinstance(pct, int)


class TestDigestLabelPresentation:
    def test_new_falling_rising_labels_preserved(self):
        assert _delta_label(30, 0) == "new"
        assert _delta_label(900, 950) == "▼ -5%"
        assert _delta_label(340, 120) == "▲ +183%"

    def test_equal_nonzero_reads_steady(self):
        assert _delta_label(5, 5) == "steady"

    def test_all_zero_now_reads_steady_not_new(self):
        # Behavior change: the digest used to return "new" for (0, 0) because it
        # checked prior==0 before current==prior. Unified policy -> "steady".
        assert _delta_label(0, 0) == "steady"
