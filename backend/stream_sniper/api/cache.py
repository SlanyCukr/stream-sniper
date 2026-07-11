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
from functools import wraps
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Purge expired entries lazily on write once the store grows past this many keys,
# so short-TTL/high-churn keys (e.g. search autocomplete) can't accumulate.
_PRUNE_THRESHOLD = 1000


class InProcessCache:
    """
    Process-local caching layer with intelligent key management and TTL settings.
    Thread-safe (sync endpoints run in Starlette's threadpool).
    """

    def __init__(self):
        """Initialize the in-memory store."""
        self.enabled = True
        # key -> (expires_at_epoch, json_serialized_value)
        self._store: Dict[str, Tuple[float, str]] = {}
        self._lock = threading.RLock()

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Generate a consistent cache key from prefix and parameters.

        Args:
            prefix: Cache key prefix (e.g., 'stream', 'chatter')
            *args: Positional arguments for key generation
            **kwargs: Keyword arguments for key generation

        Returns:
            Consistent cache key string
        """
        # Create a deterministic key from arguments
        key_data = {"args": args, "kwargs": sorted(kwargs.items()) if kwargs else {}}

        # Hash the data for consistent keys
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        key_hash = hashlib.md5(key_string.encode()).hexdigest()[:16]

        return f"stream_sniper:{prefix}:{key_hash}"

    def _prune_expired(self, now: float) -> None:
        """Drop expired entries. Caller must hold the lock."""
        expired = [k for k, (expires_at, _) in self._store.items() if expires_at <= now]
        for k in expired:
            self._store.pop(k, None)

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
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
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default: 1 hour)

        Returns:
            True if successful, False otherwise
        """
        try:
            serialized = json.dumps(value, default=str)
        except (TypeError, ValueError) as e:
            logger.warning(f"Cache set failed to serialize key {key}: {e}")
            return False

        now = time.time()
        with self._lock:
            if len(self._store) >= _PRUNE_THRESHOLD:
                self._prune_expired(now)
            self._store[key] = (now + ttl, serialized)
        return True

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if a key was removed, False otherwise
        """
        with self._lock:
            return self._store.pop(key, None) is not None

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a glob pattern.

        Args:
            pattern: Pattern to match (e.g., 'stream_sniper:stream:*')

        Returns:
            Number of keys deleted
        """
        with self._lock:
            keys = [k for k in self._store if fnmatch.fnmatchcase(k, pattern)]
            for k in keys:
                self._store.pop(k, None)
        return len(keys)

    def flush_all(self) -> bool:
        """
        Flush all cache entries in our namespace.

        Returns:
            True if successful, False otherwise
        """
        deleted = self.delete_pattern("stream_sniper:*")
        logger.info(f"Flushed {deleted} cache entries")
        return True

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics and health info.

        Returns:
            Dictionary with cache statistics
        """
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


# Global cache instance
_cache_instance: Optional[InProcessCache] = None


def get_cache() -> InProcessCache:
    """
    Get the global in-process cache instance.

    Returns:
        InProcessCache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = InProcessCache()
    return _cache_instance


def cache_result(prefix: str, ttl: int = 3600):
    """
    Decorator for caching function results.

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds

    Usage:
        @cache_result('stream_analytics', ttl=1800)
        def get_stream_analytics(stream_id):
            # expensive operation
            return result
    """

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache = get_cache()

            # Generate cache key
            cache_key = cache._generate_key(prefix, *args, **kwargs)

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Cache hit for {func.__name__} with key {cache_key}")
                return cached_result

            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl)
            logger.debug(f"Cache miss for {func.__name__}, cached with key {cache_key}")

            return result

        return wrapper

    return decorator


def invalidate_cache_pattern(pattern: str) -> int:
    """
    Invalidate cache entries matching a pattern.

    Args:
        pattern: Pattern to match for invalidation

    Returns:
        Number of keys invalidated
    """
    cache = get_cache()
    return cache.delete_pattern(f"stream_sniper:{pattern}")


def warm_cache():
    """
    Warm the cache with frequently accessed data.
    This function can be called on application startup.
    """
    logger.info("Starting cache warming process...")

    try:
        # Import here to avoid circular imports
        from ..database.creator_table_gateway import select_creators_db
        from ..database.stream_table_gateway import select_all_stream_count_db

        cache = get_cache()

        # Warm creators cache
        creators = select_creators_db()
        if creators:
            cache_key = cache._generate_key("creators")
            cache.set(cache_key, creators, ttl=7200)  # 2 hours
            logger.info(f"Warmed creators cache with {len(creators)} entries")

        # Warm stream counts for common creator_ids
        for creator_id in [-1, 1, 2, 3]:  # -1 for all creators, then top few
            try:
                count = select_all_stream_count_db(creator_id)
                # Seed the FULL-arity key an unfiltered /streams request generates
                # (creator_id + the four None filters), so the pre-warm is actually read.
                cache_key = cache._generate_key("stream_count", creator_id, None, None, None, None)
                cache.set(cache_key, count, ttl=1800)  # 30 minutes
            except Exception:
                continue

        logger.info("Cache warming completed successfully")

    except Exception as e:
        logger.warning(f"Cache warming failed: {e}")


# Cache TTL constants
class CacheTTL:
    """Cache TTL constants for different data types."""

    # Basic data (rarely changes)
    CREATORS = 7200  # 2 hours
    STREAM_COUNT = 1800  # 30 minutes

    # Analytics data (moderate changes)
    STREAM_ANALYTICS = 3600  # 1 hour
    MOST_ACTIVE_CHATTERS = 3600  # 1 hour
    MOST_TAGGED_CHATTERS = 3600  # 1 hour

    # Detailed data (frequent access)
    STREAM_DETAILS = 1800  # 30 minutes
    CHATTER_MESSAGES = 1800  # 30 minutes

    # Search / autocomplete (short-lived, high churn)
    CHATTER_SEARCH = 300  # 5 minutes
    TWITCH_SEARCH = 60  # 1 minute

    # Volatile data
    HEALTH_CHECK = 300  # 5 minutes
    LIVE_STATS = 60  # 1 minute
