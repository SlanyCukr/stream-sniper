"""API server entry point."""

import uvicorn

from ..logging_config import get_logger, setup_logging


def run() -> int:
    """Run the API server."""
    setup_logging(environment="production")
    logger = get_logger(__name__)

    try:
        from .asgi import app

        config = app.state.config
        logger.info(f"Starting Stream Sniper API server on {config.host}:{config.port}")

        uvicorn.run(
            app,
            host=config.host,
            port=config.port,
            log_config=None,  # Disable uvicorn's default logging to use our structured logging
            access_log=False,  # We handle access logging in middleware
        )
        return 0
    except Exception as e:
        logger.error(f"Failed to start API server: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    raise SystemExit(run())
