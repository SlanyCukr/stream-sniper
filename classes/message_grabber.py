import twitch
import logging
from datetime import datetime
import time

from database.message_grabbing import select_creator_id_db, insert_new_creator_db, insert_new_chatter_db, \
    insert_message_db, insert_stream_db
from utils.message_grabbing_utils import find_tagged_user_id
from utils.twitch_api_utils import get_stream_info

CLIENT_ID = "0f3ad54dd9ffmhwjoiulu39c3ql5f7"


class MessageGrabber:
    def __init__(self, channel: str):
        self.creator_id = None
        self.stream_id = None
        self.creator_name = channel
        self.channel = f"#{channel}"
        self.known_chatters = {}

        logging.basicConfig(filename=f"{channel}.log", format='%(asctime)s %(message)s', filemode='w')
        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)

    def update_stream_info(self, stream_info):
        stream_id = insert_stream_db(
            int(stream_info['id']),
            datetime.strptime(stream_info['started_at'], '%Y-%m-%dT%H:%M:%SZ'),
            self.creator_id
        )
        self.stream_id = stream_id

    def insert_creator(self):
        creator_id = select_creator_id_db(self.creator_name)

        # this creator isn't in the database yet
        if not creator_id:
            self.logger.debug("Creator is not in database yet. Creating...")

            new_creator_id = insert_new_creator_db(self.creator_name)
            if not new_creator_id:
                self.logger.error(f"Can't create new creator with name {self.creator_name}. Exiting...")
                exit(1)
            self.creator_id = new_creator_id

        self.creator_id = creator_id

    def handle_message(self, message):
        nick = message.sender
        text = message.text

        if nick not in self.known_chatters:
            chatter_id = insert_new_chatter_db(nick)
            self.known_chatters[nick] = chatter_id
            self.logger.info(f"Found new chatter {nick}.")

        tagged_user_id = find_tagged_user_id(text, self.known_chatters)
        insert_message_db(self.known_chatters[nick], tagged_user_id, self.stream_id, text)

        print(f"{nick} - {text}")

    def start(self):
        while True:
            stream_info = get_stream_info(self.channel)
            if stream_info:
                self.logger.info("Stream is UP, collecting messages.")
                break

            time.sleep(10)

        self.insert_creator()
        self.update_stream_info(stream_info[0])

        twitch.Chat(channel=self.channel, nickname='HarekM', oauth=f'oauth:{CLIENT_ID}').subscribe(self.handle_message)
