import sys
import logging

from classes.twitch_collector_facade import TwitchCollectorFacade

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

    twitch_collector_facade = TwitchCollectorFacade(nickname)
    twitch_collector_facade.start_processing()
