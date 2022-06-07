import logging

from classes.chat_downloader import ChatDownloader
from classes.chat_processor import ChatProcessor
from classes.message_handler import MessageHandler
from database.message_grabbing import select_creator_id_db, insert_new_creator_db
from utils.utils import twitch_datetime_str_to_datetime


class TwitchCollectorFacade:
    def __init__(self, nickname: str):
        self.nickname = nickname

        self.insert_creator()

        self.message_handler = MessageHandler(nickname)
        self.chat_processor = ChatProcessor(
            nickname, self.creator_id,
            self.message_handler.handle_nick, self.message_handler.handle_message,
        )
        self.chat_downloader = ChatDownloader(nickname)
        self.creator_id = -1

    def start_processing(self):
        while True:
            try:
                downloaded_chat_path, twitch_stream_id, started_at = self.chat_downloader.download_chat()
            except:
                # we are out of videos
                break

            # current video can't be processed
            if not downloaded_chat_path:
                continue

            self.chat_processor.process_file(downloaded_chat_path, twitch_stream_id, twitch_datetime_str_to_datetime(started_at))

    def insert_creator(self):
        creator_id = select_creator_id_db(self.nickname)

        # this creator isn't in the database yet
        if not creator_id:
            logging.debug("Creator is not in database yet. Creating...")

            new_creator_id = insert_new_creator_db(self.nickname)
            if not new_creator_id:
                logging.error(f"Can't create new creator with name {self.nickname}. Exiting...")
                exit(1)
            creator_id = new_creator_id

        self.creator_id = creator_id
