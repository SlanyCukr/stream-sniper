import logging

from database.message_grabbing import insert_new_chatter_db, insert_message_db
from utils.message_grabbing_utils import find_tagged_user_id


class MessageHandler:
    def __init__(self, creator_nick: str):
        self.known_chatters = {}

        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)

        # creator should be cached in known_chatters from the start
        creator_id = insert_new_chatter_db(creator_nick)
        self.known_chatters[creator_nick] = creator_id

    def handle_nick(self, chatter_nick: str):
        if chatter_nick not in self.known_chatters:
            chatter_id = insert_new_chatter_db(chatter_nick)
            self.known_chatters[chatter_nick] = chatter_id

    def handle_message(self, message_timestamp, chatter_nick, message, stream_id):
        tagged_user_id = find_tagged_user_id(message, self.known_chatters)
        insert_message_db(self.known_chatters[chatter_nick], tagged_user_id, stream_id, message, message_timestamp)
