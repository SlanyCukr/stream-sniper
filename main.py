import sys
import logging


from classes.message_grabber import MessageGrabber
from classes.message_handler import MessageHandler

if __name__ == '__main__':
    nickname = sys.argv[1]

    logging.basicConfig(filename=f"{nickname}.log", format='%(asctime)s %(message)s', filemode='w')

    message_handler = MessageHandler()
    message_grabber = MessageGrabber(nickname, message_handler.update_stream_id)
    message_grabber.message_handling_fun = message_handler.handle_message
    message_grabber.start()
