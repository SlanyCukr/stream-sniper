import asyncio
import os
from typing import Any, List, Optional, Tuple, Union

from twitchAPI.object.api import Stream, TwitchUser
from twitchAPI.twitch import Twitch
from twitchAPI.type import VideoType


class TwitchAPI:
    _instance = None

    def __init__(self):
        self._init_lock = asyncio.Lock()
        self.streamer_nickname: Optional[str] = None

    @classmethod
    def instance(cls):
        """Process-wide shared client for long-lived concurrent callers (the API).

        Only this constructor path assigns the singleton: privately constructed
        instances (collector facade, stream monitor) must never become the shared
        client, since their sessions may be bound to short-lived worker loops and
        their nickname state is mutated freely.
        """
        if cls._instance is None:
            cls._instance = TwitchAPI()
        return cls._instance

    def set_streamer_nickname(self, streamer_nickname: str):
        self.streamer_nickname = streamer_nickname

    def _resolve_login(self, login: Optional[str]) -> str:
        """Resolve the per-call login, falling back to the instance nickname.

        Raises instead of silently querying whichever streamer the nickname
        state last pointed at (or none at all) — shared-instance callers must
        pass the login explicitly.
        """
        resolved = login if login is not None else self.streamer_nickname
        if not resolved:
            raise ValueError("No Twitch login provided and no streamer nickname set")
        return resolved

    async def twitch_api_init(self):
        client_id = os.environ.get("TWITCH_CLIENT_ID")
        client_secret = os.environ.get("TWITCH_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise RuntimeError(
                "TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET environment variables must be set"
            )
        self.twitch = await Twitch(client_id, client_secret)

    async def ensure_initialized(self):
        """
        Initialize the Twitch client once and reuse it (idempotent).
        Long-lived callers such as the API process (channel-search autocomplete,
        add-streamer) should use this to avoid re-running the OAuth handshake on
        every request. The reused aiohttp session stays bound to the API's single
        event loop, which is where these coroutines are awaited.
        """
        if getattr(self, "twitch", None) is None:
            # Guard against concurrent first requests each running the OAuth
            # handshake and leaking all but one client session.
            async with self._init_lock:
                if getattr(self, "twitch", None) is None:
                    await self.twitch_api_init()

    async def search_channels_async(self, query: str, limit: int = 8) -> List[Any]:
        """
        Search Twitch channels by name for autocomplete. Returns SearchChannelResult
        objects (broadcaster_login, display_name, id, is_live, thumbnail_url, ...).
        Only channels that streamed within the past 6 months are returned by Twitch.
        """
        results: List[Any] = []
        async for channel in self.twitch.search_channels(query, first=limit):
            results.append(channel)
            if len(results) >= limit:
                break
        return results

    @staticmethod
    def get_async_result(async_generator, return_all_values: bool = False) -> Union[List, Any]:
        """
        Get the first value from an async generator
        :param async_generator: The async generator to get the first value from
        :param return_all_values: If True, return all values from the async generator
        :return: The first value from the async generator
        """

        async def get_first_value(async_gen, return_all_values):
            returned_values = []

            async for value in async_gen:
                returned_values.append(value)
                if not return_all_values:
                    return returned_values[0]
            return returned_values

        try:
            # Try to get the current running loop
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create a new one
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        # Run the internal async function to get the first value from the async generator
        return loop.run_until_complete(get_first_value(async_generator, return_all_values))

    def get_creator_twitch_id(self):
        response: TwitchUser = self.get_async_result(self.twitch.get_users(logins=[self.streamer_nickname]))

        return response.id

    def get_creator_info(self) -> Tuple[str, str]:
        response: TwitchUser = self.get_async_result(self.twitch.get_users(logins=[self.streamer_nickname]))

        return response.display_name, response.profile_image_url

    def get_stream_info(self) -> Stream:
        stream: Stream = self.get_async_result(self.twitch.get_streams(user_login=self.streamer_nickname))

        return stream

    def get_available_video_ids(self) -> List[dict]:
        twitch_user_id = self.get_creator_twitch_id()
        videos = self.get_async_result(
            self.twitch.get_videos(user_id=twitch_user_id, video_type=VideoType.ARCHIVE), return_all_values=True
        )

        if videos is None:
            return []

        return videos

    # Async variants for callers that already run inside an event loop (the
    # FastAPI endpoints and the tracking monitor). The sync get_async_result
    # helper above uses loop.run_until_complete, which raises "This event loop
    # is already running" when called from async code — and the Twitch client's
    # aiohttp session is bound to the running loop, so the coroutines must be
    # awaited on that same loop rather than bridged from a worker thread.
    #
    # Each takes an optional per-call ``login``: callers sharing the singleton
    # (the concurrent FastAPI handlers) must pass it instead of mutating the
    # shared ``set_streamer_nickname`` state, which interleaved requests could
    # overwrite between the set and the awaited lookup.
    async def get_creator_twitch_id_async(self, login: Optional[str] = None) -> Any:
        async for user in self.twitch.get_users(logins=[self._resolve_login(login)]):
            return user.id
        return None

    async def get_creator_info_async(self, login: Optional[str] = None) -> Optional[Tuple[str, str]]:
        """Return (display_name, profile_image_url), or None if the login doesn't exist."""
        async for user in self.twitch.get_users(logins=[self._resolve_login(login)]):
            return user.display_name, user.profile_image_url
        return None

    async def get_stream_info_async(self, login: Optional[str] = None) -> Any:
        async for stream in self.twitch.get_streams(user_login=[self._resolve_login(login)]):
            return stream
        return None

    async def get_available_video_ids_async(self, login: Optional[str] = None) -> List[Any]:
        twitch_user_id = await self.get_creator_twitch_id_async(login)
        if twitch_user_id is None:
            return []
        videos = []
        async for video in self.twitch.get_videos(user_id=twitch_user_id, video_type=VideoType.ARCHIVE):
            videos.append(video)
        return videos
