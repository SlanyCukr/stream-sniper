import logging

from database.message_grabbing import insert_new_chatter_db, insert_message_db
from utils.message_grabbing_utils import find_tagged_user_id


class MessageHandler:
    def __init__(self, creator_nick: str):
        self.known_chatters = {}
        self.stream_id = -1

        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)

        # creator should be cached in known_chatters from the start
        creator_id = insert_new_chatter_db(creator_nick)
        self.known_chatters[creator_nick] = creator_id

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

    def update_stream_id(self, stream_id):
        self.stream_id = stream_id
