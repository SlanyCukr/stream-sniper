import asyncio
from typing import List, Tuple, Union, Any

from twitchAPI.object.api import TwitchUser, Stream
from twitchAPI.type import VideoType
from twitchAPI.twitch import Twitch


class TwitchAPI:
    _instance = None

    def __init__(self):
        if not TwitchAPI._instance:
            TwitchAPI._instance = self

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = TwitchAPI()
        return cls._instance

    def set_streamer_nickname(self, streamer_nickname: str):
        self.streamer_nickname = streamer_nickname

    async def twitch_api_init(self):
        self.twitch = await Twitch("9c7juru6rfbukm213trck2mlxwsip5", "52uj87wai8vi71g1zup0q0no6kv7dg")

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
