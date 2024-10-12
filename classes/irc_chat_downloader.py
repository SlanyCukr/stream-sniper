import logging
from typing import Tuple, Union, List
from twitch.helix import Video
from chat_downloader import ChatDownloader

from classes.twitch_api import TwitchAPI
from database.stream_table_gateway import select_stream_by_twitch_id_db


class IrcChatDownloader:
    def __init__(self, nickname: str):
        self.nickname = nickname
        self.available_video_ids = TwitchAPI.instance().get_available_video_ids()
        self.downloader = ChatDownloader()

    def download_chat(self) -> Union[Tuple[None, None, None, None, None, None], Tuple[List[dict], str, str, str, str, str]]:
        while True:
            # no available videos
            if len(self.available_video_ids) == 0:
                return None, None, None, None, None, None

            currently_processed_video: Video = self.available_video_ids.pop(0)

            # available video was already processed - is in the database
            if select_stream_by_twitch_id_db(currently_processed_video.id):
                logging.debug("Available video is already processed - is in the database.")
                continue

            video_id = currently_processed_video.id
            logging.debug(f"Downloading chat for video with ID {video_id}.")

            chat = self.downloader.get_chat(f"https://www.twitch.tv/videos/{video_id}", format="json", message_receive_timeout=0.01, buffer_size=16384)
            chat_iterated = [x for x in chat]

            logging.debug("Chat downloaded, moving on.")

            returned_tuple = (
                chat_iterated,
                currently_processed_video.id,
                currently_processed_video.created_at,
                currently_processed_video.title,
                currently_processed_video.duration,
                currently_processed_video.thumbnail_url
            )

            return returned_tuple
