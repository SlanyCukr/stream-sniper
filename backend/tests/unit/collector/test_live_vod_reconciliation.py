from datetime import datetime
from types import SimpleNamespace

import pytest

from stream_sniper.collector.archived import twitch_vod_chat_downloader as downloader_module
from stream_sniper.collector.archived.twitch_vod_chat_downloader import (
    TwitchVodChatDownloader,
    VodChatDownloadError,
)
from stream_sniper.collector.twitch_api import ArchivedVideo


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
    downloader = TwitchVodChatDownloader.__new__(TwitchVodChatDownloader)
    downloader.available_videos = [video]
    downloader.logger = SimpleNamespace(info=lambda *args: None, debug=lambda *args: None)
    downloader.chat_client = SimpleNamespace(
        open_messages=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not download"))
    )
    monkeypatch.setattr(downloader_module, "select_live_stream_by_session_db", lambda session: (77, True))
    monkeypatch.setattr(
        downloader_module,
        "reconcile_live_stream_vod_db",
        lambda *args: reconciled.append(args),
    )

    result = downloader.open_chat_stream()

    assert result is None
    assert reconciled == [(123, 987, "thumb")]


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
