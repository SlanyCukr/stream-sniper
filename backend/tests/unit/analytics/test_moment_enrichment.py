"""Unit tests for moment enrichment (window math + jsonb shapes; gateway mocked)."""

from datetime import datetime, timedelta
from unittest.mock import patch

from stream_sniper.analytics.moment_enrichment import enrich_moments

_BASE = datetime(2024, 1, 15, 20, 0, 0)
_FMT = "%Y-%m-%dT%H:%M:%S"


def _iso(minute_offset: int) -> str:
    return (_BASE + timedelta(minutes=minute_offset)).strftime(_FMT)


def _spike_buckets():
    # 10 flat minutes then a spike at minute 10 -> exactly one detected moment (bucket_minute=_iso(10)).
    buckets = [(_iso(i), 5, 3, 0, 0) for i in range(10)]
    buckets.append((_iso(10), 100, 40, 0, 0))
    return buckets


_MODULE = "stream_sniper.analytics.moment_enrichment.select_moment_window_messages_db"


class TestEnrichMoments:
    def test_no_moments_returns_empty_without_query(self):
        flat = [(_iso(i), 5, 3, 0, 0) for i in range(10)]
        with patch(_MODULE) as mock_q:
            assert enrich_moments(7, flat, _iso(0), {}, set()) == []
        mock_q.assert_not_called()

    def test_window_shares_and_jsonb_shapes(self):
        t10 = _BASE + timedelta(minutes=10)
        rows = [
            (t10, "insane play", 1, True, 2),
            (t10, "insane play", 2, True, None),
            (t10, "insane play", 3, False, 1),
            (t10, "boring", 4, None, None),
        ]
        phrase_usage = {"insane play": 1, "insane": 1, "play": 1, "boring": 1}

        with patch(_MODULE, return_value=rows):
            result = enrich_moments(7, _spike_buckets(), _iso(0), phrase_usage, set())

        assert len(result) == 1
        row = result[0]
        assert len(row) == 10
        (bucket_minute, _offset, message_count, _baseline, _ratio, _unique, sub_share, emote_share, top_phrases, samples) = row

        assert bucket_minute == _iso(10)
        assert message_count == 100  # spike-minute count, not window total
        assert sub_share == 0.5  # 2 of 4 messages is_subscriber True
        assert emote_share == 0.5  # 2 of 4 messages carry emote_count

        assert isinstance(top_phrases, list) and len(top_phrases) <= 5
        assert set(top_phrases[0].keys()) == {"phrase", "count", "lift"}
        assert any(p["phrase"] == "insane play" for p in top_phrases)

        assert samples == [{"text": "insane play", "count": 3}, {"text": "boring", "count": 1}]

    def test_single_query_for_all_windows(self):
        # Two spikes far enough apart to be two moments -> still exactly one gateway call.
        buckets = [(_iso(i), 5, 3, 0, 0) for i in range(10)]
        buckets.append((_iso(10), 100, 40, 0, 0))
        buckets += [(_iso(i), 5, 3, 0, 0) for i in range(11, 30)]
        buckets.append((_iso(30), 120, 50, 0, 0))

        with patch(_MODULE, return_value=[]) as mock_q:
            result = enrich_moments(7, buckets, _iso(0), {}, set())

        mock_q.assert_called_once()
        windows = mock_q.call_args[0][1]
        assert len(windows) == 2  # one window per moment
        assert len(result) == 2

    def test_empty_window_yields_null_enrichment(self):
        with patch(_MODULE, return_value=[]):
            result = enrich_moments(7, _spike_buckets(), _iso(0), {}, set())
        (_bm, _off, _mc, _bl, _r, _u, sub_share, emote_share, top_phrases, samples) = result[0]
        assert sub_share is None and emote_share is None
        assert top_phrases is None and samples is None
