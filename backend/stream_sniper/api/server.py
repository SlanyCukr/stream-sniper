"""API server entry point."""

import sys

import uvicorn

from ..logging_config import get_logger, setup_logging

# Setup structured logging for production
setup_logging(environment="production")


def run():
    """Run the API server."""
    logger = get_logger(__name__)

    try:
        from .api import app
        from .config import get_config

        config = get_config()
        logger.info(f"Starting Stream Sniper API server on {config.host}:{config.port}")

        uvicorn.run(
            app,
            host=config.host,
            port=config.port,
            log_config=None,  # Disable uvicorn's default logging to use our structured logging
            access_log=False,  # We handle access logging in middleware
        )
    except Exception as e:
        logger.error(f"Failed to start API server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    run()
