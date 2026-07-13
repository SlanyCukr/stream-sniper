"""Tests for deterministic scene-event derivation and digest formatting."""

import json
from decimal import Decimal
from unittest.mock import patch

from stream_sniper.analytics.digest import format_digest
from stream_sniper.analytics.scene_events import refresh_stream_events


@patch("stream_sniper.analytics.scene_events.replace_stream_scene_events_db")
@patch("stream_sniper.analytics.scene_events.select_stream_event_signals_db")
def test_refresh_builds_report_records_moment_and_spread(signals, replace):
    signals.return_value = (
        (42, 5, "Alice", "Big show", "2024-01-02T22:00:00", 2000, 300, 20.0, 1500, 250, 18.0),
        ("2024-01-02T21:00:00", 6.5, 120),
        [(99, "legendary pasta", 12, 3)],
    )

    count = refresh_stream_events(42)

    assert count == 6
    events = replace.call_args.args[1]
    assert {event["event_type"] for event in events} == {
        "stream_report", "personal_record", "standout_moment", "copypasta_spread"
    }
    assert len({event["dedupe_key"] for event in events}) == 6
    assert next(e for e in events if e["event_type"] == "copypasta_spread")["message_text_id"] == 99


@patch("stream_sniper.analytics.scene_events.replace_stream_scene_events_db")
@patch("stream_sniper.analytics.scene_events.select_stream_event_signals_db")
def test_refresh_normalizes_database_decimals_for_json(signals, replace):
    signals.return_value = (
        (
            42,
            5,
            "Alice",
            "Big show",
            "2024-01-02T22:00:00",
            2000,
            300,
            Decimal("20.25"),
            1500,
            250,
            Decimal("18.5"),
        ),
        None,
        [],
    )

    refresh_stream_events(42)

    events = replace.call_args.args[1]
    json.dumps([event["metadata"] for event in events])


@patch("stream_sniper.analytics.scene_events.replace_stream_scene_events_db")
@patch("stream_sniper.analytics.scene_events.select_stream_event_signals_db")
def test_unrolled_stream_clears_events(signals, replace):
    signals.return_value = ((42, 5, "Alice", "No rollup", "2024-01-02T22:00:00", None, None, None, None, None, None), None, [])
    assert refresh_stream_events(42) == 0
    replace.assert_called_once_with(42, [])


def test_digest_is_deterministic_markdown():
    rows = [(1, "personal_record", "2024-01-02T22:00:00", 5, "alice", "Alice", 42, None, "New record", "2,000", {})]
    digest = format_digest(rows, 7)
    assert digest.startswith("## Stream Sniper · 7-day scene pulse")
    assert "**New record**" in digest
    assert "Alice" in digest
