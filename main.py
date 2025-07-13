#!/usr/bin/env python3
"""
Legacy entry point for Stream Sniper.
This file is deprecated. Use 'stream-sniper' command after installing the package.
"""

import sys
from dotenv import load_dotenv

from stream_sniper.collector import TwitchCollectorFacade
from stream_sniper.logging_config import setup_logging, get_logger

load_dotenv()

if __name__ == '__main__':
    # Set up structured logging
    setup_logging(environment='development')
    logger = get_logger(__name__)
    
    logger.warning("This entry point is deprecated. Use 'stream-sniper' command after installing the package.")
    
    if len(sys.argv) < 2:
        logger.error("Missing required argument: twitch_username")
        logger.info("Usage: python main.py <twitch_username>")
        sys.exit(1)
    
    nickname = sys.argv[1]
    logger.info(f"Starting Stream Sniper data collection for user: {nickname}")

    try:
        twitch_collector_facade = TwitchCollectorFacade(nickname)
        twitch_collector_facade.start_processing()
        logger.info(f"Data collection completed successfully for user: {nickname}")
    except Exception as e:
        logger.error(f"Data collection failed for user {nickname}: {e}", exc_info=True)
        sys.exit(1)
