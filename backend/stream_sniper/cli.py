"""CLI entry point for Stream Sniper."""

import sys

from .database.core.connection_pool import database_entrypoint
from .logging_config import get_logger, setup_logging


def show_help() -> None:
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


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ["--help", "-h", "help"]:
        show_help()
        return 0 if sys.argv[1:] else 1

    return _ingest_archived_vods(sys.argv[1])


@database_entrypoint
def _ingest_archived_vods(twitch_username: str) -> int:
    setup_logging(environment="development")
    logger = get_logger(__name__)
    from .collector.archived.twitch_collector_facade import TwitchCollectorFacade

    logger.info(f"Stream Sniper CLI started for user: {twitch_username}")

    try:
        twitch_collector_facade = TwitchCollectorFacade(twitch_username)
        twitch_collector_facade.ingest_archived_vods()
        logger.info(f"Data collection completed successfully for user: {twitch_username}")
        return 0
    except KeyboardInterrupt:
        logger.warning("Data collection interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Data collection failed for user {twitch_username}: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
