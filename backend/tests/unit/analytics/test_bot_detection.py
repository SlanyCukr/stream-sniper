"""Unit tests for bot classification (stream_sniper.analytics.operations.bot_detection).

Gateways and the overlap recompute are patched at the bot_detection module path; no
Postgres is touched. Covers the known-name list, the three-pass orchestrator, dry-run
behavior, reason strings, and CLI argument handling.
"""

from unittest.mock import patch

from stream_sniper.analytics.operations import bot_detection
from stream_sniper.analytics.operations.bot_detection import KNOWN_BOTS, classify_bots


class TestKnownBots:
    """Sanity checks on the curated known-bot name set."""

    def test_is_frozenset_of_lowercase_names(self):
        assert isinstance(KNOWN_BOTS, frozenset)
        for name in KNOWN_BOTS:
            assert name == name.lower()
            assert name.strip() == name
            assert " " not in name

    def test_contains_core_bots(self):
        for expected in ("nightbot", "streamelements", "streamlabs", "moobot", "fossabot"):
            assert expected in KNOWN_BOTS


class TestClassifyBots:
    """The three-pass orchestrator classify_bots()."""

    @patch("stream_sniper.analytics.operations.bot_detection.count_bots_db")
    @patch("stream_sniper.analytics.operations.bot_detection.select_bot_candidates_rate_db")
    @patch("stream_sniper.analytics.operations.bot_detection.select_bot_candidates_ubiquity_db")
    @patch("stream_sniper.analytics.operations.bot_detection.mark_bots_by_ids_db")
    @patch("stream_sniper.analytics.operations.bot_detection.mark_bots_by_nick_db")
    def test_marks_all_three_layers(self, mock_nick, mock_ids, mock_ubiq, mock_rate, mock_count):
        mock_nick.return_value = 3
        mock_ubiq.return_value = [(101, 25), (102, 30)]
        mock_rate.return_value = [(201, 5)]
        mock_count.return_value = 6

        counts = classify_bots(20)

        assert counts == {"known": 3, "ubiquity": 2, "rate": 1, "total_bots": 6}
        mock_nick.assert_called_once_with(sorted(KNOWN_BOTS), "known_bot")
        mock_ubiq.assert_called_once_with(20)
        mock_ids.assert_any_call([101, 102], "ubiquity:20")
        mock_ids.assert_any_call([201], "rate")

    @patch("stream_sniper.analytics.operations.bot_detection.count_bots_db")
    @patch("stream_sniper.analytics.operations.bot_detection.select_bot_candidates_rate_db")
    @patch("stream_sniper.analytics.operations.bot_detection.select_bot_candidates_ubiquity_db")
    @patch("stream_sniper.analytics.operations.bot_detection.mark_bots_by_ids_db")
    @patch("stream_sniper.analytics.operations.bot_detection.mark_bots_by_nick_db")
    def test_min_channels_in_reason(self, mock_nick, mock_ids, mock_ubiq, mock_rate, mock_count):
        """The ubiquity reason string carries the configured threshold."""
        mock_nick.return_value = 0
        mock_ubiq.return_value = [(101, 40)]
        mock_rate.return_value = []
        mock_count.return_value = 1

        classify_bots(35)

        mock_ubiq.assert_called_once_with(35)
        mock_ids.assert_called_once_with([101], "ubiquity:35")

    @patch("stream_sniper.analytics.operations.bot_detection.count_bots_db")
    @patch("stream_sniper.analytics.operations.bot_detection.select_bot_candidates_rate_db")
    @patch("stream_sniper.analytics.operations.bot_detection.select_bot_candidates_ubiquity_db")
    @patch("stream_sniper.analytics.operations.bot_detection.mark_bots_by_ids_db")
    @patch("stream_sniper.analytics.operations.bot_detection.mark_bots_by_nick_db")
    def test_dry_run_writes_nothing(self, mock_nick, mock_ids, mock_ubiq, mock_rate, mock_count):
        mock_ubiq.return_value = [(101, 25), (102, 30)]
        mock_rate.return_value = [(201, 5)]
        mock_count.return_value = 0

        counts = classify_bots(20, dry_run=True)

        mock_nick.assert_not_called()
        mock_ids.assert_not_called()
        assert counts["known"] == len(KNOWN_BOTS)
        assert counts["ubiquity"] == 2
        assert counts["rate"] == 1


class TestMainCli:
    """CLI argument handling in main()."""

    @patch("stream_sniper.analytics.operations.bot_detection.recompute_creator_overlap")
    @patch("stream_sniper.analytics.operations.bot_detection.classify_bots")
    def test_default_run_recomputes_overlap(self, mock_classify, mock_recompute):
        mock_classify.return_value = {"known": 1, "ubiquity": 0, "rate": 0, "total_bots": 1}

        with patch("sys.argv", ["stream-sniper-classify-bots"]):
            assert bot_detection.main.__wrapped__() == 0

        mock_classify.assert_called_once_with(20, dry_run=False)
        mock_recompute.assert_called_once_with(blocking=True)

    @patch("stream_sniper.analytics.operations.bot_detection.recompute_creator_overlap")
    @patch("stream_sniper.analytics.operations.bot_detection.classify_bots")
    def test_dry_run_skips_recompute(self, mock_classify, mock_recompute):
        mock_classify.return_value = {"known": 0, "ubiquity": 0, "rate": 0, "total_bots": 0}

        with patch("sys.argv", ["stream-sniper-classify-bots", "--dry-run"]):
            assert bot_detection.main.__wrapped__() == 0

        mock_classify.assert_called_once_with(20, dry_run=True)
        mock_recompute.assert_not_called()

    @patch("stream_sniper.analytics.operations.bot_detection.recompute_creator_overlap")
    @patch("stream_sniper.analytics.operations.bot_detection.classify_bots")
    def test_min_channels_and_skip_flag(self, mock_classify, mock_recompute):
        mock_classify.return_value = {"known": 0, "ubiquity": 0, "rate": 0, "total_bots": 0}

        with patch(
            "sys.argv",
            ["stream-sniper-classify-bots", "--min-channels", "40", "--skip-overlap-recompute"],
        ):
            assert bot_detection.main.__wrapped__() == 0

        mock_classify.assert_called_once_with(40, dry_run=False)
        mock_recompute.assert_not_called()
