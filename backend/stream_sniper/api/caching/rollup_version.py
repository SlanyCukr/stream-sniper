"""Rollup-version cache-key parts for cross-process invalidation.

The API cache is in-process, but analytics rollups (timeline buckets, emote
and phrase stats, moments, overlap, creator aggregates) are written by the
separate collector/tracking process — an entry cached before a rollup would
otherwise stay stale for its full TTL. Including the relevant rollup version
(``stream_metrics.computed_at``, exposed as opaque epoch text) in the cache
key makes every recomputation start a fresh key; superseded entries simply
age out via TTL and the lazy prune.

Each helper degrades to a constant sentinel instead of raising: a failed
version probe must never take down an endpoint that could still serve the
request (and if the database is truly down, the endpoint's main query fails
with a proper error right after). The sentinel keys behave exactly like the
pre-versioning cache.
"""

from ...database.gateways.analytics.stream_metrics_table_gateway import (
    select_creator_rollup_version_db,
    select_scene_rollup_version_db,
    select_stream_creator_rollup_version_db,
    select_stream_rollup_version_db,
)
from ...logging_config import get_logger

logger = get_logger(__name__)

_UNVERSIONED = "unversioned"


def _resolve(probe_name: str, probe) -> str:
    try:
        return probe() or _UNVERSIONED
    except Exception:
        logger.warning("Rollup version probe %s failed; caching without a version part", probe_name)
        return _UNVERSIONED


def stream_rollup_version(stream_id: int) -> str:
    """Version part for responses derived from one stream's rollup tables."""
    return _resolve("stream", lambda: select_stream_rollup_version_db(stream_id))


def stream_creator_rollup_version(stream_id: int) -> str:
    """Version part for responses mixing one stream with its creator baseline."""
    return _resolve("stream_creator", lambda: select_stream_creator_rollup_version_db(stream_id))


def creator_rollup_version(creator_id: int) -> str:
    """Version part for creator-scoped rollup responses (trends, regulars, ...)."""
    return _resolve("creator", lambda: select_creator_rollup_version_db(creator_id))


def scene_rollup_version() -> str:
    """Version part for scene-wide rollup responses (leaderboard, overlap, ...)."""
    return _resolve("scene", select_scene_rollup_version_db)
