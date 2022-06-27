import logging

from classes.chat_downloader import ChatDownloader
from classes.chat_processor import ChatProcessor
from classes.message_handler import MessageHandler
from database.creator_table_gateway import select_creator_id_db, insert_new_creator_db
from classes.database_buffer import DatabaseBuffer
from database.message_table_gateway import insert_message_db
from utils.message_grabbing_utils import update_stream_info
from utils.twitch_api_utils import get_creator_info
from utils.utils import twitch_datetime_str_to_datetime


class TwitchCollectorFacade:
    def __init__(self, nickname: str):
        self.nickname = nickname

        self.creator_id = -1
        self.insert_creator_get_id()

        self.db_buffer = DatabaseBuffer(insert_message_db, 5000)
        self.message_handler = MessageHandler(nickname, self.db_buffer.add_item)
        self.chat_processor = ChatProcessor(
            self.creator_id, self.message_handler.handle_nick,
            self.message_handler.handle_message
        )
        self.chat_downloader = ChatDownloader(nickname)

    def start_processing(self):
        while True:
            downloaded_chat_path, twitch_stream_id, started_at, title,\
            duration, thumbnail_url = self.chat_downloader.download_chat()

            # all videos have been processed
            if not downloaded_chat_path:
                break

            started_at = twitch_datetime_str_to_datetime(started_at)

            # transform stream data, insert it into database
            stream_id = update_stream_info(twitch_stream_id, started_at, self.creator_id, title, duration, thumbnail_url)

            # process the messages in downloaded file
            self.chat_processor.process_file(downloaded_chat_path, started_at, stream_id)

        # send all hanging items in buffer to database
        self.db_buffer.call_db_function()

    def insert_creator_get_id(self):
        creator_id = select_creator_id_db(self.nickname)

        # this creator isn't in the database yet
        if not creator_id:
            logging.debug("Creator is not in database yet. Creating...")

            display_name, profile_image_url = get_creator_info(self.nickname)
            new_creator_id = insert_new_creator_db(self.nickname, display_name, profile_image_url)
            if not new_creator_id:
                logging.error(f"Can't create new creator with name {self.nickname}. Exiting...")
                exit(1)
            creator_id = new_creator_id

        self.creator_id = creator_id
