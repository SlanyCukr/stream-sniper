"""Contract tests for async Twitch access and the collector sync bridge."""

import asyncio
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from stream_sniper.collector.twitch_api import (
    ArchivedVideo,
    SyncTwitchClient,
    TwitchAPI,
    TwitchOperationError,
)


class FakeTwitch:
    def __init__(self) -> None:
        self.user_calls: list[str] = []

    def get_users(self, *, logins):
        login = logins[0]
        self.user_calls.append(login)

        async def values():
            await asyncio.sleep(0)
            if login != "missing":
                yield SimpleNamespace(
                    id=f"id-{login}",
                    display_name=login.title(),
                    profile_image_url=f"https://img/{login}",
                )

        return values()

    def get_videos(self, *, user_id, video_type):
        async def values():
            yield SimpleNamespace(
                id="11",
                stream_id="22",
                created_at="2024-01-15T20:00:00Z",
                title=f"Archive for {user_id}",
                duration="1h",
                thumbnail_url="thumb",
            )
            yield SimpleNamespace(
                id="12",
                stream_id=None,
                created_at=datetime(2024, 1, 16, 20),
                title="Second",
                duration="2h",
                thumbnail_url="thumb2",
            )

        return values()


@pytest.mark.asyncio
async def test_concurrent_initialization_runs_oauth_once(monkeypatch):
    client = TwitchAPI()
    initialize = AsyncMock()

    async def install_client():
        await initialize()
        client.twitch = FakeTwitch()  # type: ignore[assignment]

    monkeypatch.setattr(client, "_initialize_client", install_client)

    await asyncio.gather(*(client.ensure_initialized() for _ in range(8)))

    initialize.assert_awaited_once()


@pytest.mark.asyncio
async def test_concurrent_logins_do_not_share_mutable_state():
    client = TwitchAPI()
    fake = FakeTwitch()
    client.twitch = fake  # type: ignore[assignment]

    alice, bob = await asyncio.gather(
        client.get_creator_profile("alice"),
        client.get_creator_profile("bob"),
    )

    assert alice is not None and alice.twitch_user_id == "id-alice"
    assert bob is not None and bob.twitch_user_id == "id-bob"
    assert fake.user_calls == ["alice", "bob"]


@pytest.mark.asyncio
async def test_archived_videos_are_normalized_and_missing_user_is_empty():
    client = TwitchAPI()
    client.twitch = FakeTwitch()  # type: ignore[assignment]

    videos = await client.get_archived_videos("alice")

    assert videos == [
        ArchivedVideo(
            11,
            22,
            datetime.fromisoformat("2024-01-15T20:00:00+00:00"),
            "Archive for id-alice",
            "1h",
            "thumb",
        ),
        ArchivedVideo(12, None, datetime(2024, 1, 16, 20), "Second", "2h", "thumb2"),
    ]
    assert await client.get_archived_videos("missing") == []


@pytest.mark.asyncio
async def test_missing_credentials_fail_before_client_creation(monkeypatch):
    monkeypatch.delenv("TWITCH_CLIENT_ID", raising=False)
    monkeypatch.delenv("TWITCH_CLIENT_SECRET", raising=False)

    with pytest.raises(TwitchOperationError, match="TWITCH_CLIENT_ID"):
        await TwitchAPI()._initialize_client()


@pytest.mark.asyncio
async def test_unexpected_programming_error_is_not_reclassified():
    client = TwitchAPI()
    client.twitch = SimpleNamespace(get_users=lambda **_kwargs: (_ for _ in ()).throw(TypeError("bug")))  # type: ignore[assignment]

    with pytest.raises(TypeError, match="bug"):
        await client.get_creator_profile("alice")


@pytest.mark.asyncio
async def test_sync_bridge_rejects_running_event_loop():
    with pytest.raises(RuntimeError, match="running event loop"):
        SyncTwitchClient()


def test_sync_bridge_owns_one_loop_for_collector_calls():
    async_client = SimpleNamespace(
        ensure_initialized=AsyncMock(),
        get_creator_profile=AsyncMock(return_value=None),
        get_archived_videos=AsyncMock(return_value=[]),
        close=AsyncMock(),
    )
    client = SyncTwitchClient(async_client)  # type: ignore[arg-type]

    client.initialize()
    assert client.get_creator_profile("alice") is None
    assert client.get_archived_videos("alice") == []
    client.close()

    async_client.ensure_initialized.assert_awaited_once()
    async_client.get_creator_profile.assert_awaited_once_with("alice")
    async_client.get_archived_videos.assert_awaited_once_with("alice")
    async_client.close.assert_awaited_once()
