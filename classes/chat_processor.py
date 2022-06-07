import logging
import os

from tqdm import tqdm

from database.message_grabbing import insert_stream_db
from utils.utils import add_timedelta_to_point_in_time

CLIENT_ID = "0f3ad54dd9ffmhwjoiulu39c3ql5f7"


class ChatProcessor:
    def __init__(self, channel: str, creator_id: int, nick_handling_fun, message_handling_fun):
        self.creator_id = creator_id
        self.stream_id = None
        self.creator_name = channel
        self.channel = f"#{channel}"
        self.chat_file_path = ""
        self.twitch_stream_id = ""
        self.started_at = ""

        self.nick_handling_fun = nick_handling_fun
        self.message_handling_fun = message_handling_fun

        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)

    def update_stream_info(self):
        stream_id = insert_stream_db(
            self.twitch_stream_id,
            self.started_at,
            self.creator_id,
        )
        self.stream_id = stream_id

    def process_file_nick_only(self):
        """
        Is used to populate dictionary with nicks and their IDs in MessageHandler.
        :return:
        """
        file = open(self.chat_file_path, "r")

        for line in tqdm(file.readlines()):
            split_line = line.split(' ')
            chatter_nick = split_line[1][2:-1]

            self.nick_handling_fun(chatter_nick)

        file.close()

    def process_file(self, chat_file_path, twitch_stream_id, started_at):
        self.chat_file_path = chat_file_path
        self.twitch_stream_id = twitch_stream_id
        self.started_at = started_at

        self.update_stream_info()
        self.process_file_nick_only()

        file = open(self.chat_file_path, "r")

        for line in tqdm(file.readlines()):
            split_line = line.split(' ')
            start_of_message_index = line.find('>') + 2

            time_str = split_line[0][1:-1]
            chatter_nick = split_line[1][2:-1]
            message = line[start_of_message_index:-1]
            message = message[:255]

            message_time = add_timedelta_to_point_in_time(started_at, time_str)

            self.message_handling_fun(message_time, chatter_nick, message, self.stream_id)

        file.close()
        os.remove(chat_file_path)
