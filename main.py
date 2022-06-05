import sys

from classes.message_grabber import MessageGrabber

if __name__ == '__main__':
    nickname = sys.argv[1]

    opat_grabber = MessageGrabber(nickname)
    opat_grabber.start()
