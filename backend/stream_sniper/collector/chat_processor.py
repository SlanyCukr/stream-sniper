from datetime import datetime, UTC
from typing import Callable, List

from tqdm import tqdm

from ..logging_config import get_logger


class ChatProcessor:
    def __init__(self, creator_id: int, message_handling_fun: Callable):
        self.creator_id = creator_id
        self.message_handling_fun = message_handling_fun
        self.logger = get_logger(__name__)

    def get_nicks(self, chat: List[str]):
        """¨
        :return:
        """
        self.logger.debug("Processing nicks.")

        chatter_nicks = []
        for line in chat:
            if line['author'] == {}:
                continue

            if 'name' not in line['author']:
                chatter_nicks.append('Unknown')
                continue

            chatter_nick = line['author']['name']

            chatter_nicks.append(chatter_nick)

        return list(set(chatter_nicks))

    def get_messages(self, chat: List[str]):
        """
        :return:
        """

        messages = []
        for line in chat:
            message = line['message']
            messages.append(message)

        return list(set(messages))

    def process_chat(self, chat: List[dict], stream_id: int):
        self.logger.debug("Processing messages.")
        for line in tqdm(chat):
            message_time = datetime.fromtimestamp(line['timestamp'] / 1000000, UTC)

            chatter_nick = line['author'].get('name', 'Unknown')
            message = line['message']

            self.message_handling_fun(message_time, chatter_nick, message, stream_id)
