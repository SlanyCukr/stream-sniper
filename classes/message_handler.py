import logging

from database.chatter_table_gateway import insert_new_chatter_db
from database.message_text_table_gateway import find_or_insert_message_text_id_db
from utils.message_grabbing_utils import find_tagged_user_id


class MessageHandler:
    def __init__(self, creator_nick: str, insert_message_fun):
        self.known_chatters = {}
        self.insert_message_fun = insert_message_fun

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
        message_text_id = find_or_insert_message_text_id_db(message)
        self.insert_message_fun((self.known_chatters[chatter_nick], tagged_user_id, stream_id, message_text_id, message_timestamp))
