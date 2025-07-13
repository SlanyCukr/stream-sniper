"""CLI entry point for Stream Sniper."""

import sys
import logging
from dotenv import load_dotenv

from .collector import TwitchCollectorFacade


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: stream-sniper <twitch_username>")
        sys.exit(1)
    
    load_dotenv()
    
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


if __name__ == '__main__':
    main()