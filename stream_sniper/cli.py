"""CLI entry point for Stream Sniper."""

import sys
from dotenv import load_dotenv

from .collector import TwitchCollectorFacade
from .logging_config import setup_logging, get_logger


def show_help():
    """Display help information."""
    help_text = """Usage: stream-sniper <twitch_username>

Description:
  Collect and process chat data from Twitch streams for the specified username.

Arguments:
  twitch_username    The Twitch username/channel to process

Examples:
  stream-sniper shroud
  stream-sniper pokimane

Environment Variables:
  Database connection will be loaded from .env file or environment
  LOG_LEVEL          Set logging level (DEBUG, INFO, WARNING, ERROR)
  ENVIRONMENT        Set environment (development, production)"""
    
    print(help_text)


def main():
    """Main CLI entry point."""
    if len(sys.argv) < 2 or sys.argv[1] in ['--help', '-h', 'help']:
        show_help()
        if sys.argv[1:] and sys.argv[1] in ['--help', '-h', 'help']:
            sys.exit(0)
        else:
            sys.exit(1)
    
    load_dotenv()
    
    # Set up structured logging
    setup_logging(environment='development')
    logger = get_logger(__name__)
    
    nickname = sys.argv[1]
    logger.info(f"Stream Sniper CLI started for user: {nickname}")
    
    try:
        twitch_collector_facade = TwitchCollectorFacade(nickname)
        twitch_collector_facade.start_processing()
        logger.info(f"Data collection completed successfully for user: {nickname}")
    except KeyboardInterrupt:
        logger.warning("Data collection interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Data collection failed for user {nickname}: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()