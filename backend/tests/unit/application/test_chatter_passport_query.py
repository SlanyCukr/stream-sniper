"""Contract tests for chatter-passport application orchestration."""

from stream_sniper.application.chatters import passport_query
from stream_sniper.application.chatters.passport_query import get_chatter_passport
from stream_sniper.database.gateways.analytics.records import (
    ChatterActiveStreamRow,
    ChatterDebutRow,
    ChatterTimeBoundsRow,
)
from stream_sniper.database.gateways.chat.records import ChatterProfileRow
from stream_sniper.database.gateways.creators.records import ChatterLoyaltyRow


def _patch(monkeypatch, *, profile, loyalty, debut, active, time_bounds=None) -> None:
    bounds = time_bounds if time_bounds is not None else ChatterTimeBoundsRow(None, None)
    monkeypatch.setattr(passport_query, "select_chatter_profile_db", lambda _cid: profile)
    monkeypatch.setattr(passport_query, "select_chatter_loyalty_db", lambda _cid: loyalty)
    monkeypatch.setattr(passport_query, "select_chatter_debut_db", lambda _cid: debut)
    monkeypatch.setattr(passport_query, "select_chatter_most_active_stream_db", lambda _cid: active)
    monkeypatch.setattr(passport_query, "select_chatter_message_time_bounds_db", lambda _cid: bounds)


def test_unknown_chatter_returns_none(monkeypatch) -> None:
    _patch(monkeypatch, profile=None, loyalty=[], debut=None, active=None)
    assert get_chatter_passport(999) is None


def test_assembles_totals_loyalty_and_shares(monkeypatch) -> None:
    loyalty = [
        ChatterLoyaltyRow(5, "homie", "Homie", 800, 12, "2024-01-01T00:00:00", "2024-06-01T00:00:00"),
        ChatterLoyaltyRow(9, "other", "Other", 200, 3, "2024-02-01T00:00:00", "2024-05-01T00:00:00"),
    ]
    _patch(
        monkeypatch,
        profile=ChatterProfileRow(42, "chatty", False, None),
        loyalty=loyalty,
        debut=ChatterDebutRow(7, "First Stream", "Homie", "2024-01-01T20:00:00"),
        active=ChatterActiveStreamRow(11, "Big One", "Homie", 350),
        # Message-time bounds intentionally differ from the loyalty rows' stream-start
        # first/last_seen: totals must reflect MESSAGE times (the debut, not stream start).
        time_bounds=ChatterTimeBoundsRow("2024-01-01T20:00:00", "2024-06-01T13:37:00"),
    )

    result = get_chatter_passport(42)
    assert result is not None

    assert result.chatter.id == 42
    assert result.chatter.nick == "chatty"
    assert result.chatter.is_bot is False

    assert result.totals.messages == 1000
    assert result.totals.streams_attended == 15
    assert result.totals.creators_visited == 2
    # From message-time bounds, NOT the loyalty rows' stream-start columns:
    # first_seen equals the debut message time even though the attended stream
    # started earlier ("2024-01-01T00:00:00" in the loyalty row).
    assert result.totals.first_seen == "2024-01-01T20:00:00"
    assert result.totals.last_seen == "2024-06-01T13:37:00"

    # loyalty preserves gateway order (messages desc) and computes share = messages / totals.messages
    assert [entry.creator_id for entry in result.loyalty] == [5, 9]
    assert result.loyalty[0].share == 0.8
    assert result.loyalty[1].share == 0.2

    # home channel is the top loyalty row
    assert result.home_channel is not None
    assert result.home_channel.creator_id == 5
    assert result.home_channel.messages == 800
    assert result.home_channel.share == 0.8

    assert result.debut is not None
    assert result.debut.stream_id == 7
    assert result.debut.time == "2024-01-01T20:00:00"

    assert result.milestones.most_active_stream is not None
    assert result.milestones.most_active_stream.stream_id == 11
    assert result.milestones.most_active_stream.messages == 350

    # Archetypes are derived from the assembled totals/home share. home_share 0.8 with
    # 15 streams -> loyalist; first_seen in 2024 is always >180d before now -> veteran.
    # 1000/15 avg < 100 and 1000 < 5000 so marathoner/chatterbox do NOT apply.
    keys = [badge.key for badge in result.archetypes]
    assert keys == ["loyalist", "veteran"]


def test_empty_corpus_yields_zero_share_and_null_milestones(monkeypatch) -> None:
    _patch(
        monkeypatch,
        profile=ChatterProfileRow(42, "quiet", None, None),
        loyalty=[],
        debut=None,
        active=None,
    )

    result = get_chatter_passport(42)
    assert result is not None
    assert result.totals.messages == 0
    assert result.totals.creators_visited == 0
    assert result.totals.first_seen is None
    assert result.totals.last_seen is None
    assert result.loyalty == []
    assert result.home_channel is None
    assert result.debut is None
    assert result.milestones.most_active_stream is None
    assert result.chatter.is_bot is None
    # No corpus -> no archetypes (empty totals, no home share, no first_seen).
    assert result.archetypes == []


def test_totals_seen_come_from_message_time_bounds(monkeypatch) -> None:
    loyalty = [
        ChatterLoyaltyRow(5, "a", "A", 100, 2, None, None),
        ChatterLoyaltyRow(9, "b", "B", 50, 1, "2024-03-01T00:00:00", "2024-03-02T00:00:00"),
    ]
    _patch(
        monkeypatch,
        profile=ChatterProfileRow(1, "x", True, "known-bot"),
        loyalty=loyalty,
        debut=None,
        active=None,
        time_bounds=ChatterTimeBoundsRow("2024-03-01T18:05:00", "2024-03-02T02:10:00"),
    )

    result = get_chatter_passport(1)
    assert result is not None
    assert result.totals.first_seen == "2024-03-01T18:05:00"
    assert result.totals.last_seen == "2024-03-02T02:10:00"
    assert result.chatter.is_bot is True
    assert result.chatter.bot_reason == "known-bot"
