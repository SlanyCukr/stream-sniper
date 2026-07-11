"""Unit tests for the pure moments-detection algorithm (§4.4).

Every expected output below is computed by hand from the algorithm constants
WINDOW=10, SPIKE_MULTIPLIER=3.0, MIN_ABSOLUTE=15, MIN_GAP_MINUTES=5.
"""

from datetime import datetime, timedelta

from stream_sniper.api.moments import detect_moments

_BASE = datetime(2024, 1, 15, 20, 0, 0)


def _iso(minute_offset: int) -> str:
    return (_BASE + timedelta(minutes=minute_offset)).strftime("%Y-%m-%dT%H:%M:%S")


def _bucket(minute_offset: int, count: int, unique: int):
    return (_iso(minute_offset), count, unique)


class TestSpikeDetection:
    def test_single_spike_above_baseline(self):
        # Minutes 0-9 sit at 5 msgs (never clear MIN_ABSOLUTE=15). Minute 10 spikes to 100.
        # window for minute 10 = ten 5s -> median 5.0 -> threshold max(15, 15)=15; 100 >= 15.
        buckets = [_bucket(i, 5, 3) for i in range(10)]
        buckets.append(_bucket(10, 100, 40))
        buckets.append(_bucket(11, 5, 3))

        moments = detect_moments(buckets, _iso(0))

        assert len(moments) == 1
        moment = moments[0]
        assert moment.bucket_minute == _iso(10)
        assert moment.message_count == 100
        assert moment.baseline == 5.0
        assert moment.ratio == 20.0  # round(100 / 5, 2)
        assert moment.unique_chatters == 40
        assert moment.offset_seconds == 600  # 10 minutes after stream_start

    def test_low_traffic_never_flagged(self):
        # A whole stream that never clears MIN_ABSOLUTE yields no moments.
        buckets = [_bucket(i, 9, 2) for i in range(20)]

        assert detect_moments(buckets, _iso(0)) == []

    def test_offset_from_first_bucket_when_start_none(self):
        buckets = [_bucket(i, 5, 3) for i in range(10)]
        buckets.append(_bucket(10, 100, 40))

        moments = detect_moments(buckets, None)

        assert len(moments) == 1
        # offset measured from the first bucket (minute 0) -> 600 seconds.
        assert moments[0].offset_seconds == 600


class TestGapCollapse:
    def test_nearby_spikes_collapse_far_spikes_separate(self):
        # Baseline 5 for minutes 0-20, with spikes at 10 (50), 12 (100), 20 (60).
        counts = {10: 50, 12: 100, 20: 60}
        buckets = [_bucket(i, counts.get(i, 5), 3) for i in range(21)]

        moments = detect_moments(buckets, _iso(0))

        # Minutes 10 and 12 are within MIN_GAP_MINUTES(5) -> collapse to the highest (minute 12).
        # Minute 20 is 8 minutes after 12 -> its own group.
        assert len(moments) == 2
        assert moments[0].bucket_minute == _iso(12)
        assert moments[0].message_count == 100
        assert moments[1].bucket_minute == _iso(20)
        assert moments[1].message_count == 60

    def test_tie_keeps_earliest(self):
        # Two equal-height spikes within the gap window: earliest wins.
        counts = {10: 80, 13: 80}
        buckets = [_bucket(i, counts.get(i, 5), 3) for i in range(15)]

        moments = detect_moments(buckets, _iso(0))

        assert len(moments) == 1
        assert moments[0].bucket_minute == _iso(10)


class TestBaselineFloor:
    def test_baseline_zero_yields_none_ratio(self):
        # A lone bucket: empty window -> baseline 0.0 -> ratio None (no divide-by-zero).
        buckets = [_bucket(0, 20, 5)]

        moments = detect_moments(buckets, _iso(0))

        assert len(moments) == 1
        assert moments[0].baseline == 0.0
        assert moments[0].ratio is None
        assert moments[0].message_count == 20


class TestMissingMinuteZeroFill:
    def test_gap_zero_fills_and_collapses_baseline(self):
        # Buckets only at minute 0 (30 msgs) and minute 10 (20 msgs); minutes 1-9 are absent.
        # Zero-filling makes minute 10's window = [30, 0, 0, 0, 0, 0, 0, 0, 0, 0] -> median 0.0
        # -> threshold max(0, 15)=15 -> 20 >= 15 is a moment. Without zero-fill the window would
        # be just [30] -> threshold 90 and minute 10 would NOT be flagged.
        buckets = [_bucket(0, 30, 6), _bucket(10, 20, 4)]

        moments = detect_moments(buckets, _iso(0))

        assert len(moments) == 2
        assert moments[0].bucket_minute == _iso(0)
        assert moments[1].bucket_minute == _iso(10)
        assert moments[1].baseline == 0.0
        assert moments[1].ratio is None
        assert moments[1].offset_seconds == 600


def test_empty_buckets_returns_empty():
    assert detect_moments([], None) == []
    assert detect_moments([], _iso(0)) == []
