"""Management command for the standalone live Twitch chat collector."""

import asyncio
import signal
from contextlib import suppress

from ...database.core.connection_pool import async_database_entrypoint
from ...logging_config import get_logger, setup_logging


@async_database_entrypoint
async def main() -> None:
    setup_logging(environment="production")
    logger = get_logger(__name__)
    from .live_chat_collector import LiveChatCollector

    collector = LiveChatCollector()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(collector.stop()))
    logger.info("Starting standalone live chat capture")
    await collector.start()


def run_live_service() -> int:
    asyncio.run(main())
    return 0


if __name__ == "__main__":
    raise SystemExit(run_live_service())
