"""
Tracking service management command for running the automated stream tracking system.
"""

import asyncio
import signal
import sys

from dotenv import load_dotenv

from .logging_config import get_logger, setup_logging
from .tracking.scheduler import get_scheduler


def setup_signal_handlers(scheduler, logger):
    """Setup signal handlers for graceful shutdown using the running event loop."""
    loop = asyncio.get_running_loop()

    def _handle_signal(signum):
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        loop.create_task(scheduler.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal, sig)
        except NotImplementedError:
            # add_signal_handler is not available on some platforms (e.g. Windows)
            signal.signal(sig, lambda s, f: _handle_signal(s))


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
        setup_signal_handlers(scheduler, logger)
        
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