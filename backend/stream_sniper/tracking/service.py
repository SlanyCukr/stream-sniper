"""
Tracking service management command for running the automated stream tracking system.
"""

import asyncio
import logging
import signal
from typing import TYPE_CHECKING

from ..database.core.connection_pool import async_database_entrypoint
from ..logging_config import get_logger, setup_logging

if TYPE_CHECKING:
    from .scheduler import TrackingScheduler


def setup_signal_handlers(scheduler: TrackingScheduler, logger: logging.Logger) -> None:
    """Setup signal handlers for graceful shutdown using the running event loop."""
    loop = asyncio.get_running_loop()

    def _handle_signal(signum: int) -> None:
        logger.info(f"Received signal {signum}, shutting down gracefully...")
        loop.create_task(scheduler.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _handle_signal, sig)
        except NotImplementedError:
            # add_signal_handler is not available on some platforms (e.g. Windows)
            signal.signal(sig, lambda s, f: _handle_signal(s))


@async_database_entrypoint
async def main() -> int:
    setup_logging(environment="production")
    logger = get_logger(__name__)
    from .scheduler import TrackingScheduler

    logger.info("Starting Stream Sniper Tracking Service...")

    try:
        scheduler = TrackingScheduler()

        setup_signal_handlers(scheduler, logger)
        await scheduler.start()
        return 0
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down...")
        return 0
    except Exception as e:
        logger.error(f"Fatal error in tracking service: {e}", exc_info=True)
        return 1
    finally:
        logger.info("Tracking service stopped")


def run_tracking_service() -> int:
    try:
        return asyncio.run(main())
    except KeyboardInterrupt:
        print("Tracking service interrupted by user")
        return 0
    except Exception as e:
        print(f"Error starting tracking service: {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(run_tracking_service())
