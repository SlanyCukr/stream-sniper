import asyncio
from itertools import batched
from typing import Optional

from ..database.chatter_table_gateway import insert_new_chatters_db, select_all_chatters_db
from ..database.creator_table_gateway import insert_new_creator_db, select_creator_id_db
from ..database.message_table_gateway import insert_message_db
from ..database.message_text_table_gateway import insert_message_texts_db, select_all_message_texts_db
from ..database.stream_table_gateway import update_stream_message_count_db
from ..logging_config import get_logger, performance_timer
from ..utils.message_grabbing_utils import update_stream_info
from .chat_processor import ChatProcessor
from .database_buffer import DatabaseBuffer
from .irc_chat_downloader import IrcChatDownloader
from .message_handler import MessageHandler
from .twitch_api import TwitchAPI


class CreatorCreationError(Exception):
    """Raised when a creator cannot be created in the database."""


# Messages processed per batch. A full VOD from a large streamer can be
# millions of messages; materializing them all OOMs the RPI, so the chat
# iterator is consumed in chunks (~1-2 KB per parsed message → tens of MB
# peak per batch).
CHAT_BATCH_SIZE = 20_000


class TwitchCollectorFacade:
    def __init__(self, nickname: str):
        self.nickname = nickname
        self.logger = get_logger(__name__)
        self.creator_id = -1

        self.logger.info(f"Initializing Twitch collector for: {nickname}")

        self.twitch_api = TwitchAPI()
        self.twitch_api.set_streamer_nickname(nickname)

        # Run the async function synchronously
        asyncio.run(self.twitch_api.twitch_api_init())

        self.insert_creator_get_id()

        self.db_buffer_insert_message = DatabaseBuffer(insert_message_db, 5000)
        self.message_handler = MessageHandler(nickname, self.db_buffer_insert_message.add_item)
        self.chat_processor = ChatProcessor(self.creator_id, self.message_handler.handle_message)
        self.chat_downloader = IrcChatDownloader(nickname, self.twitch_api)

        self.logger.info(f"Twitch collector initialized successfully for: {nickname}")

    @performance_timer("complete_stream_processing", slow_threshold=10.0)
    def start_processing(self, max_streams: Optional[int] = None):
        self.logger.info("Starting data collection process")
        processed_streams = 0

        while True:
            if max_streams is not None and processed_streams >= max_streams:
                self.logger.info(f"Reached max_streams={max_streams}; stopping data collection")
                break
            try:
                chat, twitch_stream_id, started_at, title, duration, thumbnail_url = (
                    self.chat_downloader.download_chat()
                )

                if chat is None:
                    self.logger.debug("No more videos to process. Exiting...")
                    break

                self.logger.info(f"Processing stream: {title} (ID: {twitch_stream_id})")

                # transform stream data, insert it into database
                stream_id = update_stream_info(
                    twitch_stream_id, started_at, self.creator_id, title, duration, thumbnail_url
                )

                # Consume the chat iterator in batches instead of materializing
                # the whole VOD (OOM risk on the RPI for multi-hour streams).
                num_of_messages = 0
                for batch in batched(chat, CHAT_BATCH_SIZE, strict=False):
                    chat_batch = list(batch)

                    # process nicks
                    nicks = self.chat_processor.get_nicks(chat_batch)
                    insert_new_chatters_db(nicks)
                    known_chatters = select_all_chatters_db()
                    self.message_handler.set_known_chatters(known_chatters)
                    self.logger.debug(f"Processed {len(nicks)} unique nicknames")

                    # process messages
                    messages = self.chat_processor.get_messages(chat_batch)
                    insert_message_texts_db(messages)
                    known_messages = select_all_message_texts_db()
                    self.message_handler.set_known_messages(known_messages)
                    self.logger.debug(f"Processed {len(messages)} unique messages")

                    # process the messages in fetched chat
                    self.chat_processor.process_chat(chat_batch, stream_id)
                    num_of_messages += len(chat_batch)
                    self.logger.info(
                        f"Processed batch of {len(chat_batch)} messages for stream {twitch_stream_id} "
                        f"({num_of_messages} total so far)"
                    )

                self.logger.info(f"Processed {num_of_messages} chat messages for stream {twitch_stream_id}")

                # add number of messages to stream
                update_stream_message_count_db(stream_id, num_of_messages)

                # send all hanging items in buffer to database
                self.db_buffer_insert_message.call_db_function()

                processed_streams += 1
                self.logger.info(
                    f"Successfully processed stream {twitch_stream_id}. Total streams processed: {processed_streams}"
                )

            except KeyboardInterrupt:
                self.logger.warning("Processing interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"Error processing stream: {e}", exc_info=True)
                # Continue with next stream instead of stopping completely
                continue

        self.logger.info(f"Data collection completed. Total streams processed: {processed_streams}")

    def insert_creator_get_id(self):
        creator_id = select_creator_id_db(self.nickname)

        # this creator isn't in the database yet
        if not creator_id:
            self.logger.debug("Creator is not in database yet. Creating...")

            try:
                display_name, profile_image_url = self.twitch_api.get_creator_info()
                twitch_creator_id = self.twitch_api.get_creator_twitch_id()
                new_creator_id = insert_new_creator_db(
                    self.nickname, display_name, profile_image_url, twitch_creator_id
                )
                if not new_creator_id:
                    self.logger.error(f"Can't create new creator with name {self.nickname}.")
                    raise CreatorCreationError(f"Failed to create creator {self.nickname}")
                creator_id = new_creator_id
                self.logger.info(f"Created new creator in database: {self.nickname} (ID: {creator_id})")
            except CreatorCreationError:
                raise
            except Exception as e:
                self.logger.error(f"Failed to create creator {self.nickname}: {e}", exc_info=True)
                raise CreatorCreationError(f"Failed to create creator {self.nickname}") from e
        else:
            self.logger.info(f"Found existing creator in database: {self.nickname} (ID: {creator_id})")

        self.creator_id = creator_id
