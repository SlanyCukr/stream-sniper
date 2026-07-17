"""Unit tests for bot classification (stream_sniper.analytics.operations.bot_detection).

Gateways, the overlap recompute, and the targeted copypasta/scene-event refresh are
patched at the bot_detection module path; no Postgres is touched. Covers the known-name
list, the three-pass orchestrator, dry-run behavior, reason strings, the post-marking
stream refresh, and CLI argument handling.
"""

from unittest.mock import call, patch

from stream_sniper.analytics.operations import bot_detection
from stream_sniper.analytics.operations.bot_detection import KNOWN_BOTS, classify_bots

_MODULE = "stream_sniper.analytics.operations.bot_detection"


def _patch_classify_gateways(**overrides):
    """Patch every gateway classify_bots touches; returns a dict of started mocks.

    Callers must pair with _stop_patches. Defaults: no candidates anywhere.
    """
    defaults = {
        "select_unmarked_known_bots_db": [],
        "select_bot_candidates_ubiquity_db": [],
        "select_bot_candidates_rate_db": [],
        "mark_bots_by_ids_db": 0,
        "select_stream_ids_for_chatters_db": [],
        "refresh_stream_copypasta_and_events": None,
        "count_bots_db": 0,
    }
    defaults.update(overrides)
    patchers = {name: patch(f"{_MODULE}.{name}", return_value=value) for name, value in defaults.items()}
    return {name: p.start() for name, p in patchers.items()}, list(patchers.values())


def _stop_patches(patchers):
    for p in patchers:
        p.stop()


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

    def test_contains_cz_scene_bots(self):
        """Content-confirmed bots active in tracked Czech channels (2026-07-17 audit)."""
        for expected in ("supibot", "restreambot", "botrixoficial", "herbot_", "spajkk_irl_bot"):
            assert expected in KNOWN_BOTS


class TestClassifyBots:
    """The three-pass orchestrator classify_bots()."""

    def test_marks_all_three_layers_and_refreshes_streams(self):
        mocks, patchers = _patch_classify_gateways(
            select_unmarked_known_bots_db=[(11, "nightbot"), (12, "blerp"), (13, "supibot")],
            select_bot_candidates_ubiquity_db=[(101, 25), (102, 30)],
            select_bot_candidates_rate_db=[(201, 5)],
            select_stream_ids_for_chatters_db=[7, 9],
            count_bots_db=6,
        )
        try:
            counts = classify_bots(20)
        finally:
            _stop_patches(patchers)

        assert counts == {"known": 3, "ubiquity": 2, "rate": 1, "streams_refreshed": 2, "total_bots": 6}
        mocks["select_unmarked_known_bots_db"].assert_called_once_with(sorted(KNOWN_BOTS))
        mocks["select_bot_candidates_ubiquity_db"].assert_called_once_with(20)
        mocks["mark_bots_by_ids_db"].assert_any_call([11, 12, 13], "known_bot")
        mocks["mark_bots_by_ids_db"].assert_any_call([101, 102], "ubiquity:20")
        mocks["mark_bots_by_ids_db"].assert_any_call([201], "rate")
        # The stream refresh targets every newly-marked chatter, across all three passes.
        mocks["select_stream_ids_for_chatters_db"].assert_called_once_with([11, 12, 13, 101, 102, 201])
        assert mocks["refresh_stream_copypasta_and_events"].call_args_list == [call(7), call(9)]

    def test_min_channels_in_reason(self):
        """The ubiquity reason string carries the configured threshold."""
        mocks, patchers = _patch_classify_gateways(
            select_bot_candidates_ubiquity_db=[(101, 40)],
            count_bots_db=1,
        )
        try:
            classify_bots(35)
        finally:
            _stop_patches(patchers)

        mocks["select_bot_candidates_ubiquity_db"].assert_called_once_with(35)
        mocks["mark_bots_by_ids_db"].assert_called_once_with([101], "ubiquity:35")

    def test_no_candidates_skips_marking_and_refresh(self):
        mocks, patchers = _patch_classify_gateways()
        try:
            counts = classify_bots(20)
        finally:
            _stop_patches(patchers)

        assert counts == {"known": 0, "ubiquity": 0, "rate": 0, "streams_refreshed": 0, "total_bots": 0}
        mocks["mark_bots_by_ids_db"].assert_not_called()
        mocks["select_stream_ids_for_chatters_db"].assert_not_called()
        mocks["refresh_stream_copypasta_and_events"].assert_not_called()

    def test_dry_run_writes_nothing_and_reports_real_candidates(self):
        """Dry-run counts actual unmarked matches — not the size of the curated list."""
        mocks, patchers = _patch_classify_gateways(
            select_unmarked_known_bots_db=[(11, "nightbot")],
            select_bot_candidates_ubiquity_db=[(101, 25), (102, 30)],
            select_bot_candidates_rate_db=[(201, 5)],
        )
        try:
            counts = classify_bots(20, dry_run=True)
        finally:
            _stop_patches(patchers)

        mocks["mark_bots_by_ids_db"].assert_not_called()
        mocks["refresh_stream_copypasta_and_events"].assert_not_called()
        assert counts["known"] == 1
        assert counts["ubiquity"] == 2
        assert counts["rate"] == 1
        assert counts["streams_refreshed"] == 0


class TestMainCli:
    """CLI argument handling in main()."""

    _COUNTS_ZERO = {"known": 0, "ubiquity": 0, "rate": 0, "streams_refreshed": 0, "total_bots": 0}

    @patch(f"{_MODULE}.recompute_creator_overlap")
    @patch(f"{_MODULE}.classify_bots")
    def test_default_run_recomputes_overlap(self, mock_classify, mock_recompute):
        mock_classify.return_value = {"known": 1, "ubiquity": 0, "rate": 0, "streams_refreshed": 2, "total_bots": 1}

        with patch("sys.argv", ["stream-sniper-classify-bots"]):
            assert bot_detection.main.__wrapped__() == 0

        mock_classify.assert_called_once_with(20, dry_run=False)
        mock_recompute.assert_called_once_with(blocking=True)

    @patch(f"{_MODULE}.recompute_creator_overlap")
    @patch(f"{_MODULE}.classify_bots")
    def test_dry_run_skips_recompute(self, mock_classify, mock_recompute):
        mock_classify.return_value = self._COUNTS_ZERO

        with patch("sys.argv", ["stream-sniper-classify-bots", "--dry-run"]):
            assert bot_detection.main.__wrapped__() == 0

        mock_classify.assert_called_once_with(20, dry_run=True)
        mock_recompute.assert_not_called()

    @patch(f"{_MODULE}.recompute_creator_overlap")
    @patch(f"{_MODULE}.classify_bots")
    def test_min_channels_and_skip_flag(self, mock_classify, mock_recompute):
        mock_classify.return_value = self._COUNTS_ZERO

        with patch(
            "sys.argv",
            ["stream-sniper-classify-bots", "--min-channels", "40", "--skip-overlap-recompute"],
        ):
            assert bot_detection.main.__wrapped__() == 0

        mock_classify.assert_called_once_with(40, dry_run=False)
        mock_recompute.assert_not_called()
