import logging
import subprocess
from datetime import datetime
from typing import Tuple, Optional

from database.stream_table_gateway import select_stream_by_twitch_id_db
from utils.twitch_api_utils import get_stream_info, find_available_video_ids


class ChatDownloader:
    def __init__(self, nickname: str):
        self.nickname = nickname
        self.available_video_ids = find_available_video_ids(nickname)

    def download_chat(self) -> Tuple[Optional[str], Optional[int], Optional[datetime], Optional[str], Optional[str], Optional[str]]:
        while True:
            # no available videos
            if len(self.available_video_ids) == 0:
                return None, None, None, None, None, None

            currently_processed_video = self.available_video_ids.pop(0)
            online_stream_info = get_stream_info(self.nickname)

            # get stream id from the online stream, or set it to -1
            online_stream_info_id = -1
            if online_stream_info:
                online_stream_info_id = online_stream_info[0]['id']

            # available video is currently running as stream, we should wait for it to be complete
            if currently_processed_video['stream_id'] == online_stream_info_id:
                logging.debug("Available video is currently running as stream, we should wait for it to be complete.")
                continue
            # available video was already processed - is in the database
            if select_stream_by_twitch_id_db(currently_processed_video['stream_id']):
                logging.debug("Available video is already processed - is in the database.")
                continue

            video_id = currently_processed_video['id']
            logging.debug(f"Downloading chat for video with ID {video_id}.")

            subprocess.call([
                'tcd', '--video', video_id, '--format', 'irc', '--client-id', 'wsasht7hzjpd39lzbdkubk6mn5xzjh',
                '--client-secret', 'cmfky1zvm9rb8dh8jz4ibueuztg7e6'
            ])

            logging.debug("Chat downloaded, moving on.")

            return f"{video_id}.log", currently_processed_video['stream_id'],\
                   currently_processed_video['created_at'], currently_processed_video['title'],\
                   currently_processed_video['duration'], currently_processed_video['thumbnail_url']
