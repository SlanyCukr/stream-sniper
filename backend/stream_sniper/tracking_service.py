"""
Tracking service management command for running the automated stream tracking system.
"""

import asyncio
import signal
import sys
from typing import Optional

from dotenv import load_dotenv

from .tracking.scheduler import get_scheduler
from .logging_config import get_logger, setup_logging


def setup_signal_handlers(scheduler):
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        asyncio.create_task(scheduler.stop())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


async def main():
    """Main entry point for the tracking service."""
    load_dotenv()
    
    # Set up structured logging
    setup_logging(environment="production")
    logger = get_logger(__name__)
    
    logger.info("Starting Stream Sniper Tracking Service...")
    
    try:
        # Get scheduler instance
        scheduler = get_scheduler()
        
        # Setup signal handlers for graceful shutdown
        setup_signal_handlers(scheduler)
        
        # Start the tracking system
        await scheduler.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
    except Exception as e:
        logger.error(f"Fatal error in tracking service: {e}", exc_info=True)
        sys.exit(1)
    finally:
        logger.info("Tracking service stopped")


def run_tracking_service():
    """Run the tracking service."""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Tracking service interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"Error starting tracking service: {e}")
        sys.exit(1)


if __name__ == "__main__":
    run_tracking_service()