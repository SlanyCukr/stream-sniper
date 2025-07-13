"""Stream Sniper - Twitch stream analytics platform."""

__version__ = "1.0.0"
__author__ = "slanycukr"

# Import main components for easy access
from .collector import TwitchCollectorFacade
from .api import app

__all__ = ["TwitchCollectorFacade", "app"]