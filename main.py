import sys
import logging


from classes.message_grabber import MessageGrabber
from classes.message_handler import MessageHandler

if __name__ == '__main__':
    nickname = sys.argv[1]

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(f"{nickname}.log"),
            logging.StreamHandler()
        ]
    )
    message_handler = MessageHandler(nickname)
    message_grabber = MessageGrabber(nickname, message_handler.update_stream_id)
    message_grabber.message_handling_fun = message_handler.handle_message
    message_grabber.start()
