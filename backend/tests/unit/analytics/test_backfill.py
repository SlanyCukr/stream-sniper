"""Behavior tests for the analytics backfill entry point."""

from unittest.mock import patch

from stream_sniper.analytics.operations import backfill


def test_backfill_reports_success_for_empty_selected_set() -> None:
    with (
        patch("sys.argv", ["stream-sniper-rollup", "--all"]),
        patch.object(backfill, "setup_logging"),
        patch.object(backfill, "select_rollup_stream_ids_db", return_value=[]),
        patch.object(backfill, "recompute_creator_overlap"),
    ):
        assert backfill.main.__wrapped__() == 0
