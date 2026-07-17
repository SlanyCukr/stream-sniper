"""Production ASGI process boundary.

Environment loading and application construction intentionally live here so
importing the reusable application factory remains side-effect free.
"""

from dotenv import load_dotenv
from fastapi import FastAPI

from ..logging_config import is_logging_configured, setup_logging
from .api import create_app
from .config import load_config


def build_production_app() -> FastAPI:
    """Load process configuration and construct the production application."""
    load_dotenv()
    if not is_logging_configured():
        setup_logging(environment="production")
    return create_app(load_config())


app = build_production_app()
