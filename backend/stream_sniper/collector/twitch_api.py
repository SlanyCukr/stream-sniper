"""Typed async Twitch client plus an explicit synchronous collector adapter."""

from __future__ import annotations

import asyncio
import os
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Self, TypeVar

from aiohttp import ClientError
from twitchAPI.object.api import SearchChannelResult, Stream, Video
from twitchAPI.twitch import Twitch
from twitchAPI.type import TwitchAPIException, VideoType

from ..application.identity.tracked_streamer_creation import CreatorProfile


class TwitchOperationError(RuntimeError):
    """Base class for expected Twitch adapter failures."""


class TwitchConfigurationError(TwitchOperationError):
    """Local Twitch credentials or client configuration are invalid."""


class TwitchUpstreamError(TwitchOperationError):
    """Twitch transport, authentication, or payload handling failed."""


EXPECTED_TWITCH_ERRORS = (TwitchAPIException, ClientError, TimeoutError, OSError, ValueError)


@dataclass(frozen=True)
class TwitchCredentials:
    """Single owner of the TWITCH_CLIENT_ID/TWITCH_CLIENT_SECRET env contract.

    Every Twitch auth flow (app-token client here, user-token live collector,
    interactive auth CLI) loads credentials through :meth:`from_env` so the
    variable names and the missing-credential error live in exactly one place.
    """

    client_id: str
    client_secret: str

    @classmethod
    def from_env(cls) -> Self:
        client_id = os.environ.get("TWITCH_CLIENT_ID")
        client_secret = os.environ.get("TWITCH_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise TwitchConfigurationError(
                "TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET environment variables must be set"
            )
        return cls(client_id=client_id, client_secret=client_secret)


@dataclass(frozen=True)
class ArchivedVideo:
    twitch_vod_id: int
    twitch_stream_session_id: int | None
    created_at: datetime
    title: str
    duration: str
    thumbnail_url: str

    @classmethod
    def from_twitch(cls, video: Video) -> Self:
        created_at = video.created_at
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        if not isinstance(created_at, datetime):
            raise ValueError(f"Twitch VOD {video.id} has no valid creation timestamp")
        return cls(
            twitch_vod_id=int(video.id),
            twitch_stream_session_id=int(video.stream_id) if getattr(video, "stream_id", None) else None,
            created_at=created_at,
            title=str(getattr(video, "title", "")),
            duration=str(getattr(video, "duration", "")),
            thumbnail_url=str(getattr(video, "thumbnail_url", "")),
        )


class TwitchAPI:
    """Async Twitch contract for event-loop-native callers."""

    def __init__(self) -> None:
        self._init_lock = asyncio.Lock()
        self.twitch: Twitch | None = None

    async def _initialize_client(self) -> None:
        credentials = TwitchCredentials.from_env()
        try:
            self.twitch = await Twitch(credentials.client_id, credentials.client_secret)
        except EXPECTED_TWITCH_ERRORS as error:
            raise TwitchUpstreamError("Failed to initialize Twitch client") from error

    async def ensure_initialized(self) -> None:
        if self.twitch is None:
            async with self._init_lock:
                if self.twitch is None:
                    await self._initialize_client()

    def _client(self) -> Twitch:
        if self.twitch is None:
            raise RuntimeError("Twitch client is not initialized")
        return self.twitch

    async def close(self) -> None:
        if self.twitch is not None:
            await self.twitch.close()
            self.twitch = None

    async def search_channels(self, query: str, limit: int = 8) -> list[SearchChannelResult]:
        try:
            results: list[SearchChannelResult] = []
            async for channel in self._client().search_channels(query, first=limit):
                results.append(channel)
                if len(results) >= limit:
                    break
            return results
        except EXPECTED_TWITCH_ERRORS as error:
            raise TwitchUpstreamError(f"Failed to search Twitch channels for {query}") from error

    async def get_creator_profile(self, login: str) -> CreatorProfile | None:
        try:
            async for user in self._client().get_users(logins=[login]):
                return CreatorProfile(
                    twitch_user_id=str(user.id),
                    display_name=str(user.display_name),
                    profile_image_url=str(user.profile_image_url),
                )
            return None
        except EXPECTED_TWITCH_ERRORS as error:
            raise TwitchUpstreamError(f"Failed to load Twitch profile for {login}") from error

    async def get_live_stream(self, login: str) -> Stream | None:
        try:
            async for stream in self._client().get_streams(user_login=[login]):
                return stream
            return None
        except EXPECTED_TWITCH_ERRORS as error:
            raise TwitchUpstreamError(f"Failed to load live Twitch stream for {login}") from error

    async def get_archived_videos(self, login: str) -> list[ArchivedVideo]:
        try:
            profile = await self.get_creator_profile(login)
            if profile is None:
                return []
            return [
                ArchivedVideo.from_twitch(video)
                async for video in self._client().get_videos(
                    user_id=profile.twitch_user_id,
                    video_type=VideoType.ARCHIVE,
                )
            ]
        except EXPECTED_TWITCH_ERRORS as error:
            # A TwitchUpstreamError from get_creator_profile propagates unchanged:
            # it is not in EXPECTED_TWITCH_ERRORS, so it is never re-wrapped here.
            raise TwitchUpstreamError(f"Failed to load archived Twitch videos for {login}") from error


T = TypeVar("T")


class SyncTwitchClient:
    """Collector-only bridge that owns one persistent event loop."""

    def __init__(self, client: TwitchAPI | None = None) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            has_running_loop = False
        else:
            has_running_loop = True

        if has_running_loop:
            raise RuntimeError("SyncTwitchClient cannot be created inside a running event loop")

        self.client = client or TwitchAPI()
        self._loop = asyncio.new_event_loop()
        self._closed = False

    def _run(self, operation: Callable[[], Awaitable[T]]) -> T:
        if self._closed:
            raise RuntimeError("SyncTwitchClient is closed")
        return self._loop.run_until_complete(operation())

    def initialize(self) -> None:
        self._run(self.client.ensure_initialized)

    def get_creator_profile(self, login: str) -> CreatorProfile | None:
        return self._run(lambda: self.client.get_creator_profile(login))

    def get_archived_videos(self, login: str) -> list[ArchivedVideo]:
        return self._run(lambda: self.client.get_archived_videos(login))

    def close(self) -> None:
        if self._closed:
            return
        try:
            self._run(self.client.close)
        finally:
            self._closed = True
            self._loop.close()
