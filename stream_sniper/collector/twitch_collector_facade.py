import asyncio
import logging

from .irc_chat_downloader import IrcChatDownloader
from .chat_processor import ChatProcessor
from .message_handler import MessageHandler
from ..database.chatter_table_gateway import insert_new_chatters_db, select_all_chatters_db
from ..database.creator_table_gateway import select_creator_id_db, insert_new_creator_db
from .database_buffer import DatabaseBuffer
from ..database.message_table_gateway import insert_message_db
from ..database.message_text_table_gateway import insert_message_texts_db, select_all_message_texts_db
from ..database.stream_table_gateway import update_stream_message_count_db
from ..utils.message_grabbing_utils import update_stream_info
from .twitch_api import TwitchAPI


class TwitchCollectorFacade:
    def __init__(self, nickname: str):
        self.nickname = nickname

        self.creator_id = -1

        self.twitch_api = TwitchAPI()
        self.twitch_api.set_streamer_nickname(nickname)

        # Run the async function synchronously
        asyncio.run(self.twitch_api.twitch_api_init())

        self.insert_creator_get_id()

        self.db_buffer_insert_message = DatabaseBuffer(insert_message_db, 5000)
        self.message_handler = MessageHandler(nickname, self.db_buffer_insert_message.add_item)
        self.chat_processor = ChatProcessor(self.creator_id, self.message_handler.handle_message)
        self.chat_downloader = IrcChatDownloader(nickname)

    def start_processing(self):
        while True:
            chat, twitch_stream_id, started_at, title, duration, thumbnail_url = self.chat_downloader.download_chat()

            if not chat:
                logging.debug("No more videos to process. Exiting...")
                break

            # transform stream data, insert it into database
            stream_id = update_stream_info(twitch_stream_id, started_at, self.creator_id, title, duration, thumbnail_url)

            # process nicks
            nicks = self.chat_processor.get_nicks(chat)
            insert_new_chatters_db(nicks)
            known_chatters = select_all_chatters_db()
            self.message_handler.set_known_chatters(known_chatters)

            # process messages
            messages = self.chat_processor.get_messages(chat)
            insert_message_texts_db(messages)
            known_messages = select_all_message_texts_db()
            self.message_handler.set_known_messages(known_messages)

            # process the messages in fetched chat
            self.chat_processor.process_chat(chat, stream_id)

            num_of_messages = len(chat)

            # add number of messages to stream
            update_stream_message_count_db(stream_id, num_of_messages)

            # send all hanging items in buffer to database
            self.db_buffer_insert_message.call_db_function()

    def insert_creator_get_id(self):
        creator_id = select_creator_id_db(self.nickname)

        # this creator isn't in the database yet
        if not creator_id:
            logging.debug("Creator is not in database yet. Creating...")

            display_name, profile_image_url = self.twitch_api.get_creator_info()
            twitch_creator_id = self.twitch_api.get_creator_twitch_id()
            new_creator_id = insert_new_creator_db(self.nickname, display_name, profile_image_url, twitch_creator_id)
            if not new_creator_id:
                logging.error(f"Can't create new creator with name {self.nickname}. Exiting...")
                exit(1)
            creator_id = new_creator_id

        self.creator_id = creator_id
