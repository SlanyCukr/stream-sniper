from datetime import datetime
from types import SimpleNamespace

import pytest

from stream_sniper.collector.archived import twitch_vod_chat_downloader as downloader_module
from stream_sniper.collector.archived.twitch_vod_chat_downloader import (
    TwitchVodChatDownloader,
    VodChatDownloadError,
)
from stream_sniper.collector.twitch_api import ArchivedVideo


def _skipping_downloader(video):
    downloader = TwitchVodChatDownloader.__new__(TwitchVodChatDownloader)
    downloader.available_videos = [video]
    downloader.logger = SimpleNamespace(
        info=lambda *args: None, debug=lambda *args: None, exception=lambda *args: None
    )
    downloader.chat_client = SimpleNamespace(
        open_messages=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not download"))
    )
    return downloader


def test_completed_live_capture_reconciles_and_skips_vod(monkeypatch):
    reconciled = []
    video = ArchivedVideo(
        twitch_vod_id=987,
        twitch_stream_session_id=123,
        thumbnail_url="thumb",
        title="title",
        created_at=datetime(2024, 1, 15, 20),
        duration="1h",
    )
    downloader = _skipping_downloader(video)
    monkeypatch.setattr(downloader_module, "select_live_stream_by_session_db", lambda session: (77, True))

    def record_reconcile(*args):
        reconciled.append(args)
        return (77, False)  # rollup consistent with the recorded end -> no recompute

    monkeypatch.setattr(downloader_module, "reconcile_live_stream_vod_db", record_reconcile)
    monkeypatch.setattr(
        downloader_module,
        "compute_stream_rollup",
        lambda *_: (_ for _ in ()).throw(AssertionError("must not recompute")),
    )

    result = downloader.open_chat_stream()

    assert result is None
    # The VOD's authoritative end (created_at + duration) rides along for end repair.
    assert reconciled == [(123, 987, "thumb", datetime(2024, 1, 15, 21))]


def test_stale_rollup_triggers_recompute(monkeypatch):
    # A swept zombie's provisional end got repaired from VOD metadata -> stream_metrics
    # disagrees with the stream row and must be recomputed.
    video = ArchivedVideo(
        twitch_vod_id=987,
        twitch_stream_session_id=123,
        thumbnail_url="thumb",
        title="title",
        created_at=datetime(2024, 1, 15, 20),
        duration="3h",
    )
    downloader = _skipping_downloader(video)
    monkeypatch.setattr(downloader_module, "select_live_stream_by_session_db", lambda session: (77, True))
    monkeypatch.setattr(downloader_module, "reconcile_live_stream_vod_db", lambda *args: (77, True))
    recomputed = []
    outcome = SimpleNamespace(require_success=lambda: None)
    monkeypatch.setattr(
        downloader_module, "compute_stream_rollup", lambda stream_id: recomputed.append(stream_id) or outcome
    )

    result = downloader.open_chat_stream()

    assert result is None
    assert recomputed == [77]


def test_failed_recompute_is_retried_on_rediscovery(monkeypatch):
    # The staleness flag is durable (stream_metrics vs the stream row), so when the first
    # recompute fails transiently, the next discovery of the same VOD sees stale again and
    # retries — the failure is never lost to a one-shot signal.
    def make_video():
        return ArchivedVideo(
            twitch_vod_id=987,
            twitch_stream_session_id=123,
            thumbnail_url="thumb",
            title="title",
            created_at=datetime(2024, 1, 15, 20),
            duration="3h",
        )

    monkeypatch.setattr(downloader_module, "select_live_stream_by_session_db", lambda session: (77, True))
    monkeypatch.setattr(downloader_module, "reconcile_live_stream_vod_db", lambda *args: (77, True))
    attempts = []

    def rollup(stream_id):
        attempts.append(stream_id)
        if len(attempts) == 1:
            raise RuntimeError("transient db failure")
        return SimpleNamespace(require_success=lambda: None)

    monkeypatch.setattr(downloader_module, "compute_stream_rollup", rollup)

    # First discovery: recompute fails, VOD is still skipped (never downloaded).
    assert _skipping_downloader(make_video()).open_chat_stream() is None
    # Second discovery: reconcile reports stale again -> retried and succeeds.
    assert _skipping_downloader(make_video()).open_chat_stream() is None
    assert attempts == [77, 77]


def test_unparseable_vod_duration_reconciles_without_end(monkeypatch):
    reconciled = []
    video = ArchivedVideo(
        twitch_vod_id=987,
        twitch_stream_session_id=123,
        thumbnail_url="thumb",
        title="title",
        created_at=datetime(2024, 1, 15, 20),
        duration="",  # Twitch occasionally returns junk; end repair must degrade to a no-op
    )
    downloader = _skipping_downloader(video)
    monkeypatch.setattr(downloader_module, "select_live_stream_by_session_db", lambda session: (77, True))

    def record_reconcile(*args):
        reconciled.append(args)
        return (77, False)

    monkeypatch.setattr(downloader_module, "reconcile_live_stream_vod_db", record_reconcile)

    result = downloader.open_chat_stream()

    assert result is None
    assert reconciled == [(123, 987, "thumb", None)]


def test_exposed_vod_chat_start_failure_is_not_reported_as_success(monkeypatch):
    video = ArchivedVideo(
        twitch_vod_id=987,
        twitch_stream_session_id=None,
        thumbnail_url="thumb",
        title="title",
        created_at=datetime(2024, 1, 15, 20),
        duration="1h",
    )
    downloader = TwitchVodChatDownloader.__new__(TwitchVodChatDownloader)
    downloader.available_videos = [video]
    downloader.logger = SimpleNamespace(
        info=lambda *args: None,
        debug=lambda *args: None,
        exception=lambda *args: None,
    )
    downloader.chat_client = SimpleNamespace(
        open_messages=lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("Twitch failed"))
    )
    monkeypatch.setattr(downloader_module, "stream_exists_by_twitch_vod_id_db", lambda _vod_id: False)

    with pytest.raises(VodChatDownloadError, match="987"):
        downloader.open_chat_stream()


def test_explicit_vod_retry_reopens_chat_when_stream_row_already_exists(monkeypatch):
    video = ArchivedVideo(
        twitch_vod_id=987,
        twitch_stream_session_id=None,
        thumbnail_url="thumb",
        title="title",
        created_at=datetime(2024, 1, 15, 20),
        duration="1h",
    )
    downloader = TwitchVodChatDownloader.__new__(TwitchVodChatDownloader)
    downloader._requested_vod_id = 987
    downloader.available_videos = [video]
    downloader.logger = SimpleNamespace(info=lambda *args: None, debug=lambda *args: None)
    downloader.chat_client = SimpleNamespace(open_messages=lambda vod_id: iter([f"message-{vod_id}"]))
    monkeypatch.setattr(downloader_module, "stream_exists_by_twitch_vod_id_db", lambda _vod_id: True)

    result = downloader.open_chat_stream()

    assert result is not None
    assert result.twitch_vod_id == 987
    assert list(result.messages) == ["message-987"]
