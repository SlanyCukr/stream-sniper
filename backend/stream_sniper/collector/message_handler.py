import typing
from datetime import datetime
from functools import lru_cache
from typing import Callable

from ..database.chatter_table_gateway import insert_new_chatter_db
from ..database.message_text_table_gateway import find_or_insert_message_text_id_db
from ..logging_config import get_logger


class MessageHandler:
    def __init__(self, creator_nick: str, insert_message_fun: Callable):
        self.known_chatters = {}
        self.known_messages = {}
        self.insert_message_fun = insert_message_fun
        self.logger = get_logger(__name__)

        # creator should be cached in known_chatters from the start
        creator_id = insert_new_chatter_db(creator_nick)
        self.known_chatters[creator_nick] = creator_id
        self.logger.debug(f"Initialized message handler for creator: {creator_nick} (ID: {creator_id})")

    @lru_cache(maxsize=128)
    def find_tagged_user_id(self, message: str) -> typing.Optional[int]:
        """
        Finds tagged user id in known chatters. Not searching in `chatter` database for performance reasons.
        Only searching for one user, I don't care if there are more tagged.
        :param message: Message from chat
        :return: ID of the tagged user
        """
        if "@" not in message:
            return None

        message = message.lower()
        at_sign_index = message.find("@")
        end_of_nick_index = message.find(" ", at_sign_index)

        if end_of_nick_index == -1:
            nick = message[at_sign_index + 1 :]
        else:
            nick = message[at_sign_index + 1 : end_of_nick_index]

        if nick in self.known_chatters:
            return self.known_chatters[nick]

    def set_known_chatters(self, known_chatters: dict):
        self.known_chatters = known_chatters

    def set_known_messages(self, known_messages: dict):
        self.known_messages = known_messages

    def handle_message(self, message_timestamp: datetime, chatter_nick: str, message: str, stream_id: int):
        tagged_user_id = self.find_tagged_user_id(message)

        if message not in self.known_messages:
            message_id = find_or_insert_message_text_id_db(message)
            self.known_messages[message] = message_id

        message_text_id = self.known_messages[message]
        self.insert_message_fun(
            (self.known_chatters[chatter_nick], tagged_user_id, stream_id, message_text_id, message_timestamp)
        )
