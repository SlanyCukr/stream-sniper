"""Contract tests for chatter head-to-head application orchestration."""

import pytest

from stream_sniper.application.chatters import versus_query
from stream_sniper.application.chatters.versus_query import (
    ChatterVersusNotFoundError,
    get_chatter_head_to_head,
)
from stream_sniper.database.gateways.analytics.records import ChatterTimeBoundsRow
from stream_sniper.database.gateways.chat.records import ChatterProfileRow
from stream_sniper.database.gateways.community.chatter_pair_gateway import ChatterPairSharedRow
from stream_sniper.database.gateways.creators.records import ChatterLoyaltyRow


def _patch(monkeypatch, *, profiles, loyalty, bounds=None, shared=None) -> None:
    """Patch the versus gateways with per-chatter-id dict lookups."""
    monkeypatch.setattr(versus_query, "select_chatter_profile_db", lambda cid: profiles.get(cid))
    monkeypatch.setattr(versus_query, "select_chatter_loyalty_db", lambda cid: loyalty.get(cid, []))
    monkeypatch.setattr(
        versus_query,
        "select_chatter_message_time_bounds_db",
        lambda cid: (bounds or {}).get(cid, ChatterTimeBoundsRow(None, None)),
    )
    monkeypatch.setattr(
        versus_query,
        "select_chatter_pair_shared_db",
        lambda _a, _b: shared if shared is not None else ChatterPairSharedRow(0, 0),
    )


def test_unknown_chatter_raises(monkeypatch) -> None:
    _patch(monkeypatch, profiles={1: ChatterProfileRow(1, "known", None, None)}, loyalty={})
    with pytest.raises(ChatterVersusNotFoundError):
        get_chatter_head_to_head(1, 999)


def test_assembles_both_sides_and_shared(monkeypatch) -> None:
    profiles = {
        1: ChatterProfileRow(1, "alpha", False, None),
        2: ChatterProfileRow(2, "beta", None, None),
    }
    loyalty = {
        1: [
            ChatterLoyaltyRow(5, "homie", "Homie", 900, 12, "2024-01-01T00:00:00", "2024-06-01T00:00:00"),
            ChatterLoyaltyRow(9, "other", "Other", 100, 3, "2024-02-01T00:00:00", "2024-05-01T00:00:00"),
        ],
        2: [ChatterLoyaltyRow(5, "homie", "Homie", 40, 4, "2024-03-01T00:00:00", "2024-04-01T00:00:00")],
    }
    bounds = {
        1: ChatterTimeBoundsRow("2024-01-01T20:00:00", "2024-06-01T13:37:00"),
        2: ChatterTimeBoundsRow("2024-03-01T10:00:00", "2024-04-01T11:00:00"),
    }
    _patch(monkeypatch, profiles=profiles, loyalty=loyalty, bounds=bounds, shared=ChatterPairSharedRow(6, 2))

    result = get_chatter_head_to_head(1, 2)

    assert result.a.chatter_id == 1
    assert result.a.nick == "alpha"
    assert result.a.is_bot is False
    assert result.a.messages == 1000
    assert result.a.streams_attended == 15
    assert result.a.creators_visited == 2
    assert result.a.first_seen == "2024-01-01T20:00:00"
    # Home channel follows the passport rules: top loyalty row, share of total messages.
    assert result.a.home_channel is not None
    assert result.a.home_channel.creator_id == 5
    assert result.a.home_channel.share == 0.9
    assert result.a.archetypes  # aggregates above the badge thresholds must yield badges

    assert result.b.chatter_id == 2
    assert result.b.is_bot is None  # nullable-means-unknown passes through
    assert result.b.messages == 40
    assert result.b.creators_visited == 1
    assert result.b.home_channel is not None
    assert result.b.home_channel.share == 1.0

    assert result.shared_streams == 6
    assert result.shared_creators == 2


def test_never_crossed_paths_is_zero_not_error(monkeypatch) -> None:
    profiles = {
        1: ChatterProfileRow(1, "alpha", None, None),
        2: ChatterProfileRow(2, "beta", None, None),
    }
    _patch(monkeypatch, profiles=profiles, loyalty={}, shared=ChatterPairSharedRow(0, 0))

    result = get_chatter_head_to_head(1, 2)

    assert result.shared_streams == 0
    assert result.shared_creators == 0
    # A chatter with no rollup rows is a legitimate all-zero side, not a 404.
    assert result.a.messages == 0
    assert result.a.home_channel is None
    assert result.a.first_seen is None
