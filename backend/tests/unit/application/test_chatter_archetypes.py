"""Threshold-coverage tests for the pure archetype rule engine.

``compute_archetypes`` is deterministic given an explicit ``now``, so every badge is
exercised at and around its boundary with no clock or database dependency.
"""

from datetime import UTC, datetime, timedelta

from stream_sniper.application.chatters.archetypes import compute_archetypes
from stream_sniper.database.core.wire_format import WIRE_TS_FORMAT

_NOW = datetime(2024, 7, 1, 12, 0, 0, tzinfo=UTC)


def _wire(days_ago: float) -> str:
    """A wire timestamp ``days_ago`` days before the fixed _NOW."""
    return (_NOW - timedelta(days=days_ago)).strftime(WIRE_TS_FORMAT)


def _keys(**kwargs) -> list[str]:
    defaults = dict(
        total_messages=0,
        streams_attended=0,
        creators_visited=0,
        home_share=None,
        first_seen=None,
        now=_NOW,
    )
    defaults.update(kwargs)
    return [badge.key for badge in compute_archetypes(**defaults)]


def test_empty_passport_yields_no_badges():
    assert compute_archetypes(
        total_messages=0,
        streams_attended=0,
        creators_visited=0,
        home_share=None,
        first_seen=None,
        now=_NOW,
    ) == []


class TestLoyalist:
    def test_applies_at_boundary(self):
        assert "loyalist" in _keys(home_share=0.70, streams_attended=3, total_messages=10)

    def test_below_share_excluded(self):
        assert "loyalist" not in _keys(home_share=0.6999, streams_attended=3)

    def test_too_few_streams_excluded(self):
        assert "loyalist" not in _keys(home_share=0.9, streams_attended=2)

    def test_none_share_excluded(self):
        assert "loyalist" not in _keys(home_share=None, streams_attended=10)


class TestWanderer:
    def test_applies_at_boundary(self):
        assert "wanderer" in _keys(creators_visited=5, home_share=0.3999, total_messages=10)

    def test_share_at_040_excluded(self):
        assert "wanderer" not in _keys(creators_visited=5, home_share=0.40)

    def test_too_few_creators_excluded(self):
        assert "wanderer" not in _keys(creators_visited=4, home_share=0.1)

    def test_loyalist_and_wanderer_mutually_exclusive(self):
        # 0.70 share can never be < 0.40, so the two share-based badges never coexist.
        keys = _keys(home_share=0.70, streams_attended=5, creators_visited=6, total_messages=10)
        assert "loyalist" in keys
        assert "wanderer" not in keys


class TestMarathoner:
    def test_applies_at_boundary(self):
        # 300 messages / 3 streams == 100 average.
        assert "marathoner" in _keys(total_messages=300, streams_attended=3)

    def test_below_average_excluded(self):
        assert "marathoner" not in _keys(total_messages=299, streams_attended=3)

    def test_too_few_streams_excluded(self):
        assert "marathoner" not in _keys(total_messages=1000, streams_attended=2)

    def test_zero_streams_no_zero_division(self):
        assert "marathoner" not in _keys(total_messages=1000, streams_attended=0)


class TestChatterbox:
    def test_applies_at_boundary(self):
        assert "chatterbox" in _keys(total_messages=5000, streams_attended=1)

    def test_below_excluded(self):
        assert "chatterbox" not in _keys(total_messages=4999)


class TestVeteranNewcomer:
    def test_veteran_at_180_days(self):
        assert "veteran" in _keys(first_seen=_wire(180))

    def test_veteran_beyond_180(self):
        assert "veteran" in _keys(first_seen=_wire(400))

    def test_just_under_180_is_neither(self):
        keys = _keys(first_seen=_wire(179))
        assert "veteran" not in keys
        assert "newcomer" not in keys

    def test_newcomer_within_30(self):
        assert "newcomer" in _keys(first_seen=_wire(10))

    def test_newcomer_at_30_boundary(self):
        assert "newcomer" in _keys(first_seen=_wire(30))

    def test_newcomer_and_veteran_mutually_exclusive(self):
        keys = _keys(first_seen=_wire(5))
        assert "newcomer" in keys
        assert "veteran" not in keys

    def test_unparseable_first_seen_ignored(self):
        keys = _keys(first_seen="not-a-timestamp")
        assert "veteran" not in keys
        assert "newcomer" not in keys

    def test_naive_now_still_works(self):
        naive_now = datetime(2024, 7, 1, 12, 0, 0)
        badges = compute_archetypes(
            total_messages=0,
            streams_attended=0,
            creators_visited=0,
            home_share=None,
            first_seen=(naive_now - timedelta(days=200)).strftime(WIRE_TS_FORMAT),
            now=naive_now,
        )
        assert [b.key for b in badges] == ["veteran"]


class TestOrderingAndCap:
    def test_stable_order(self):
        # Loyalist + Marathoner + Chatterbox + Veteran, all applicable at once.
        keys = _keys(
            total_messages=6000,
            streams_attended=3,
            creators_visited=1,
            home_share=0.9,
            first_seen=_wire(365),
        )
        assert keys == ["loyalist", "marathoner", "chatterbox", "veteran"]

    def test_capped_at_four(self):
        # Wanderer + Marathoner + Chatterbox + Veteran (4) would be the set; ensure cap holds
        # even if more ever matched. Here exactly 4 match.
        keys = _keys(
            total_messages=6000,
            streams_attended=3,
            creators_visited=5,
            home_share=0.1,
            first_seen=_wire(365),
        )
        assert len(keys) == 4
        assert keys == ["wanderer", "marathoner", "chatterbox", "veteran"]

    def test_badges_carry_label_and_description(self):
        badges = compute_archetypes(
            total_messages=6000,
            streams_attended=1,
            creators_visited=1,
            home_share=None,
            first_seen=None,
            now=_NOW,
        )
        assert len(badges) == 1
        assert badges[0].key == "chatterbox"
        assert badges[0].label == "Chatterbox"
        assert badges[0].description
