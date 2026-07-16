"""Stream Sniper Twitch analytics package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("stream-sniper")
except PackageNotFoundError:  # Source tree imported without an installed distribution.
    __version__ = "0+unknown"

__all__ = ["__version__"]
