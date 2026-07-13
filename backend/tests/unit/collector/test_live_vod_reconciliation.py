from types import SimpleNamespace

from stream_sniper.collector import irc_chat_downloader as downloader_module
from stream_sniper.collector.irc_chat_downloader import IrcChatDownloader


def test_completed_live_capture_reconciles_and_skips_vod(monkeypatch):
    reconciled = []
    video = SimpleNamespace(
        id="987", stream_id="123", thumbnail_url="thumb", title="title",
        created_at=None, duration="1h",
    )
    downloader = IrcChatDownloader.__new__(IrcChatDownloader)
    downloader.available_video_ids = [video]
    downloader.logger = SimpleNamespace(info=lambda *args: None, debug=lambda *args: None)
    downloader.downloader = SimpleNamespace(
        get_chat=lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not download"))
    )
    monkeypatch.setattr(downloader_module, "select_live_stream_by_session_db", lambda session: (77, True))
    monkeypatch.setattr(
        downloader_module,
        "reconcile_live_stream_vod_db",
        lambda *args: reconciled.append(args),
    )

    result = downloader.download_chat()

    assert result == (None, None, None, None, None, None)
    assert reconciled == [("123", "987", "thumb")]
