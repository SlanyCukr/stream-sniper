"""CLI entry point for Stream Sniper."""

import sys
import logging
from dotenv import load_dotenv

from .collector import TwitchCollectorFacade


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2 or sys.argv[1] in ['--help', '-h', 'help']:
        print("Usage: stream-sniper <twitch_username>")
        print()
        print("Description:")
        print("  Collect and process chat data from Twitch streams for the specified username.")
        print()
        print("Arguments:")
        print("  twitch_username    The Twitch username/channel to process")
        print()
        print("Examples:")
        print("  stream-sniper shroud")
        print("  stream-sniper pokimane")
        print()
        print("Environment Variables:")
        print("  Database connection will be loaded from .env file or environment")
        if sys.argv[1:] and sys.argv[1] in ['--help', '-h', 'help']:
            sys.exit(0)
        else:
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