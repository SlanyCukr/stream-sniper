"""Stream Sniper - Twitch stream analytics platform."""

__version__ = "1.0.0"
__author__ = "slanycukr"

# Components are available for import but not imported at package level
# to avoid database connection issues during import
__all__ = ["TwitchCollectorFacade", "app"]
