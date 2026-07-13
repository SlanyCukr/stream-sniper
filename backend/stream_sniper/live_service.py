"""Management command for the standalone live Twitch chat collector."""

import asyncio
import signal
from contextlib import suppress

from dotenv import load_dotenv

from .collector.live import LiveChatCollector
from .logging_config import get_logger, setup_logging


async def main() -> None:
    load_dotenv()
    setup_logging(environment="production")
    logger = get_logger(__name__)
    collector = LiveChatCollector()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(collector.stop()))
    logger.info("Starting standalone live chat capture")
    await collector.start()


def run_live_service() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    run_live_service()
