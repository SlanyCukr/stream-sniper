"""Backwards-compatible re-export.

Spike-moment detection moved to ``stream_sniper.analytics.moments`` to fix the layering
(analytics must not live under the api package). This module keeps existing imports and tests
(``from stream_sniper.api.moments import detect_moments``) working.
"""

from ..analytics.moments import (  # noqa: F401
    MIN_ABSOLUTE,
    MIN_GAP_MINUTES,
    SPIKE_MULTIPLIER,
    WINDOW,
    detect_moments,
)
