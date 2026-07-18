"""
In-process caching layer with intelligent key management and TTL settings.
Provides caching for expensive database operations and analytics queries.

This is a process-local cache (a thread-safe dict with per-entry expiry) — the app
runs as a single API process, so a shared store (Redis) is unnecessary. Values are
JSON round-tripped on set/get so callers get an isolated copy, matching the prior
Redis-backed semantics. Cache is cold after a restart and re-warms in seconds.
"""

import fnmatch
import hashlib
import json
import logging
import threading
import time
from typing import Any, TypedDict

logger = logging.getLogger(__name__)

# Purge expired entries lazily on write once the store grows past this many keys,
# so short-TTL/high-churn keys (e.g. search autocomplete) can't accumulate.
_PRUNE_THRESHOLD = 1000

# Hard ceiling on LIVE entries. Public cache-miss surfaces (scene search accepts
# arbitrary query strings) would otherwise let clients grow the store without
# bound until TTLs expire — real memory pressure on the Pi. When an insert would
# exceed this, the soonest-to-expire entries are evicted first.
_MAX_LIVE_ENTRIES = 2000


class CacheStatsPayload(TypedDict):
    enabled: bool
    status: str
    backend: str
    stream_sniper_keys: int


class InProcessCache:
    def __init__(self) -> None:
        self.enabled = True
        # key -> (expires_at_epoch, json_serialized_value)
        self._store: dict[str, tuple[float, str]] = {}
        self._lock = threading.RLock()

    def generate_key(self, prefix: str, *args: object, **kwargs: object) -> str:
        """Build a deterministic namespaced key from call arguments."""
        key_data = {"args": args, "kwargs": sorted(kwargs.items()) if kwargs else {}}
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_string.encode(), usedforsecurity=False).hexdigest()[:16]

        return f"stream_sniper:{prefix}:{key_hash}"

    def _prune_expired(self, now: float) -> None:
        """Drop expired entries. Caller must hold the lock."""
        expired = [k for k, (expires_at, _) in self._store.items() if expires_at <= now]
        for k in expired:
            self._store.pop(k, None)

    def get(self, key: str) -> Any | None:
        now = time.time()
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, serialized = entry
            if expires_at <= now:
                self._store.pop(key, None)
                return None

        try:
            return json.loads(serialized)
        except (json.JSONDecodeError, TypeError) as e:
            logger.warning(f"Cache get failed to decode key {key}: {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        try:
            serialized = json.dumps(value, default=str)
        except (TypeError, ValueError) as e:
            logger.warning(f"Cache set failed to serialize key {key}: {e}")
            return False

        now = time.time()
        with self._lock:
            if len(self._store) >= _PRUNE_THRESHOLD:
                self._prune_expired(now)
            if len(self._store) >= _MAX_LIVE_ENTRIES:
                self._evict_soonest_expiring(len(self._store) - _MAX_LIVE_ENTRIES + 1)
            self._store[key] = (now + ttl, serialized)
        return True

    def _evict_soonest_expiring(self, count: int) -> None:
        """Evict the ``count`` live entries closest to expiry. Caller holds the lock.

        Soonest-to-expire is the cheapest reasonable victim policy here: it favors
        keeping long-TTL analytics entries over short-TTL churn (search pages),
        which is exactly the split we want under a cache-filling client.
        """
        victims = sorted(self._store.items(), key=lambda item: item[1][0])[:count]
        for key, _ in victims:
            self._store.pop(key, None)

    def delete(self, key: str) -> bool:
        with self._lock:
            return self._store.pop(key, None) is not None

    def delete_pattern(self, pattern: str) -> int:
        with self._lock:
            keys = [k for k in self._store if fnmatch.fnmatchcase(k, pattern)]
            for k in keys:
                self._store.pop(k, None)
        return len(keys)

    def flush_all(self) -> None:
        """Flush all cache entries in our namespace."""
        deleted = self.delete_pattern("stream_sniper:*")
        logger.info(f"Flushed {deleted} cache entries")

    def get_stats(self) -> CacheStatsPayload:
        now = time.time()
        with self._lock:
            self._prune_expired(now)
            active_keys = len(self._store)

        return {
            "enabled": True,
            "status": "healthy",
            "backend": "in-process",
            "stream_sniper_keys": active_keys,
        }


def invalidate_cache_pattern(cache: InProcessCache, pattern: str) -> int:
    return cache.delete_pattern(f"stream_sniper:{pattern}")


# Cache TTL constants
class CacheTTL:
    """Cache TTL constants for different data types."""

    CREATORS = 7200
    STREAM_COUNT = 1800
    STREAM_ANALYTICS = 3600
    MOST_ACTIVE_CHATTERS = 3600
    MOST_TAGGED_CHATTERS = 3600
    STREAM_DETAILS = 1800
    CHATTER_MESSAGES = 1800

    # Search / autocomplete (short-lived, high churn)
    CHATTER_SEARCH = 300
    TWITCH_SEARCH = 60
    HEALTH_CHECK = 300
    LIVE_STATS = 60
