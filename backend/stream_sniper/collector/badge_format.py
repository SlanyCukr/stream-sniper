"""Canonical chat-badge text shared by the archived and live collectors.

Both ingestion paths persist badges as one comma-joined, sorted string of
``name/version`` pairs (``None`` when there are none). The formatter lives here
so the two paths cannot drift; each caller only adapts its native badge shape
(VOD dict list vs IRC tag mapping) into ``(name, version)`` pairs.
"""

from collections.abc import Iterable


def format_badge_pairs(pairs: Iterable[tuple[object, object]]) -> str | None:
    """Sorted, comma-joined ``name/version`` badge text, or None when empty."""
    formatted = sorted(f"{name}/{version}" for name, version in pairs)
    return ",".join(formatted) or None
