"""Direct tests of StreamMonitor's observation state machine.

The monitor is built around a fake Twitch client through the constructor's
``twitch_api_factory`` seam; only the free-function gateways are patched.
Covered here: the LIVE->OFFLINE processing hand-off, first-observation
semantics, UNKNOWN's preserve-previous-state contract, cycle bookkeeping,
and pruning of untracked streamers.
"""

from dataclasses import dataclass
from datetime import datetime

import pytest

import stream_sniper.tracking.stream_monitor as monitor_module
from stream_sniper.tracking.status import StreamObservation
from stream_sniper.tracking.stream_monitor import StreamMonitor


@dataclass
class _LiveInfo:
    id: str = "555001"
    title: str = "Live now"
    started_at: datetime | None = None
    viewer_count: int = 42
    game_id: str = "509658"
    game_name: str = "Just Chatting"
    language: str = "cs"
    tags: tuple[str, ...] = ()
    is_mature: bool = False


@dataclass
class _Vod:
    twitch_vod_id: str = "999123"


class FakeTwitchAPI:
    """Scriptable stand-in: one queued live-lookup result per check."""

    def __init__(self):
        self.live_results: list[object] = []
        self.archived_videos: list[_Vod] = [_Vod()]
        self.raise_upstream = False

    async def get_live_stream(self, twitch_username: str):
        if self.raise_upstream:
            raise monitor_module.TwitchUpstreamError("twitch flaked")
        return self.live_results.pop(0) if self.live_results else None

    async def get_archived_videos(self, twitch_username: str):
        return list(self.archived_videos)


@dataclass
class _Row:
    id: int = 7
    twitch_username: str = "testcreator"
    display_name: str = "TestCreator"


@pytest.fixture
def build(monkeypatch):
    """(monitor, fake_api, enqueued) with DB write gateways neutralized/recorded."""
    enqueued: list[tuple[int, int]] = []
    monkeypatch.setattr(monitor_module, "update_tracked_streamer_check_time_db", lambda *a, **kw: True)
    monkeypatch.setattr(monitor_module, "insert_live_snapshot_db", lambda **kw: True)
    monkeypatch.setattr(
        monitor_module,
        "enqueue_processing_job_db",
        lambda streamer_id, vod_id: enqueued.append((streamer_id, vod_id)) or 1,
    )

    def _build() -> tuple[StreamMonitor, FakeTwitchAPI, list[tuple[int, int]]]:
        fake = FakeTwitchAPI()
        return StreamMonitor(twitch_api_factory=lambda: fake), fake, enqueued

    return _build


@pytest.mark.asyncio
async def test_live_to_offline_queues_latest_vod_and_commits_state(build):
    monitor, fake, enqueued = build()
    row = _Row()
    # Multiple archived VODs: the FIRST (most recent) one must be selected.
    fake.archived_videos = [_Vod("999123"), _Vod("888000")]
    fake.live_results = [_LiveInfo(), None, None]

    assert await monitor._check_single_stream(row) is StreamObservation.LIVE
    assert await monitor._check_single_stream(row) is StreamObservation.OFFLINE
    assert enqueued == [(7, 999123)]
    assert monitor._last_stream_states["testcreator"] is StreamObservation.OFFLINE

    # The OFFLINE commit means the edge is not reprocessed on the next poll.
    await monitor._check_single_stream(row)
    assert enqueued == [(7, 999123)]


@pytest.mark.asyncio
async def test_stream_already_live_at_first_poll_commits_without_queuing(build):
    """First observation commits state without any transition side effect.

    (First-observation *alert* suppression is pinned in test_discord_alerts.py;
    this pins that no processing job fires and the LIVE state is committed, so
    the later real OFFLINE edge is detected exactly once.)
    """
    monitor, fake, enqueued = build()
    fake.live_results = [_LiveInfo()]

    assert await monitor._check_single_stream(_Row()) is StreamObservation.LIVE
    assert enqueued == []
    assert monitor._last_stream_states["testcreator"] is StreamObservation.LIVE


@pytest.mark.asyncio
async def test_unknown_preserves_committed_state_across_flakes(build):
    monitor, fake, enqueued = build()
    row = _Row()
    fake.live_results = [_LiveInfo()]
    await monitor._check_single_stream(row)

    fake.raise_upstream = True
    assert await monitor._check_single_stream(row) is StreamObservation.UNKNOWN
    assert monitor._last_stream_states["testcreator"] is StreamObservation.LIVE

    # The committed LIVE state survives the flake: the next OFFLINE still queues.
    fake.raise_upstream = False
    fake.live_results = [None]
    await monitor._check_single_stream(row)
    assert enqueued == [(7, 999123)]


@pytest.mark.asyncio
async def test_offline_stream_never_queues(build):
    monitor, fake, enqueued = build()
    fake.live_results = [None, None]
    await monitor._check_single_stream(_Row())
    await monitor._check_single_stream(_Row())
    assert enqueued == []


@pytest.mark.asyncio
async def test_cycle_bookkeeping_degrades_on_unknown(build, monkeypatch):
    monitor, fake, _ = build()
    monkeypatch.setattr(
        monitor_module, "select_active_tracked_streamers_db", lambda: [_Row()]
    )
    monkeypatch.setattr(monitor_module.asyncio, "sleep", _no_sleep)

    fake.live_results = [None]
    await monitor._check_all_streams()
    clean = monitor.get_monitoring_stats()
    assert (clean.successful_checks, clean.unknown_checks, clean.degraded) == (1, 0, False)
    assert clean.last_successful_cycle is not None

    fake.raise_upstream = True
    await monitor._check_all_streams()
    degraded = monitor.get_monitoring_stats()
    assert (degraded.successful_checks, degraded.unknown_checks, degraded.degraded) == (0, 1, True)
    # last_successful_cycle keeps its earlier value; a degraded cycle never advances it.
    assert degraded.last_successful_cycle == clean.last_successful_cycle


@pytest.mark.asyncio
async def test_untracked_streamers_are_pruned_from_state(build):
    monitor, fake, _ = build()
    fake.live_results = [_LiveInfo()]
    await monitor._check_single_stream(_Row())
    assert "testcreator" in monitor._last_stream_states
    # Seed alert-dedup state as a delivered "went live" alert would have.
    monitor._alerted_sessions.add(555001)
    monitor._streamer_session_ids["testcreator"] = 555001

    monitor._prune_untracked_state({"someoneelse"})
    assert "testcreator" not in monitor._last_stream_states
    assert "testcreator" not in monitor._streamer_session_ids
    assert 555001 not in monitor._alerted_sessions


async def _no_sleep(_seconds: float) -> None:
    return None
