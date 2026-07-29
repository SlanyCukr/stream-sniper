"""The wire timestamp's Python and SQL representations must agree, and the
parse/render operations are the single owner of that string's semantics."""

from datetime import UTC, datetime

import pytest

from stream_sniper.database.core.wire_format import (
    format_wire_ts,
    parse_wire_ts,
    to_char_wire,
    to_char_wire_us,
)


def test_round_trip_is_lossless_at_second_precision():
    moment = datetime(2026, 7, 28, 18, 5, 42)
    assert parse_wire_ts(format_wire_ts(moment)) == moment


def test_format_matches_the_documented_wire_shape():
    assert format_wire_ts(datetime(2026, 1, 2, 3, 4, 5)) == "2026-01-02T03:04:05"


def test_aware_datetimes_render_as_wall_clock_without_offset():
    """The wire string is tz-naive by contract: an aware input is rendered as its
    wall-clock reading and the offset is dropped (gateways emit UTC wall-clock)."""
    aware = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
    assert format_wire_ts(aware) == "2026-01-02T03:04:05"
    assert parse_wire_ts(format_wire_ts(aware)).tzinfo is None


def test_parse_rejects_the_pre_iso_space_separator():
    with pytest.raises(ValueError):
        parse_wire_ts("2026-01-02 03:04:05")


def test_sql_fragments_pin_the_exact_mask_literal():
    # Literal expectations on purpose: if either representation drifts, this fails
    # instead of both sides of a self-referential assertion moving together.
    assert to_char_wire("m.time") == "TO_CHAR(m.time, 'YYYY-MM-DD\"T\"HH24:MI:SS')"
    assert to_char_wire_us("m.time") == "TO_CHAR(m.time, 'YYYY-MM-DD\"T\"HH24:MI:SS.US')"
