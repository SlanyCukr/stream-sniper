"""
Redis caching layer with intelligent key management and TTL settings.
Provides caching for expensive database operations and analytics queries.
"""

import json
import logging
import hashlib
from typing import Any, Optional, List, Dict, Union
from datetime import datetime, timedelta
import redis
from functools import wraps
import os
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()


class RedisCache:
    """
    Redis-based caching layer with intelligent key management and TTL settings.
    Provides graceful degradation when Redis is unavailable.
    """

    def __init__(self):
        """Initialize Redis connection with configuration from environment."""
        self.redis_client = None
        self.enabled = True
        self._connect()

    def _connect(self):
        """Establish Redis connection with configuration from environment."""
        try:
            redis_config = {
                "host": os.getenv("REDIS_HOST", "localhost"),
                "port": int(os.getenv("REDIS_PORT", 6379)),
                "db": int(os.getenv("REDIS_DB", 0)),
                "decode_responses": True,
                "socket_connect_timeout": int(os.getenv("REDIS_CONNECT_TIMEOUT", 5)),
                "socket_timeout": int(os.getenv("REDIS_SOCKET_TIMEOUT", 5)),
                "retry_on_timeout": True,
                "health_check_interval": int(os.getenv("REDIS_HEALTH_CHECK_INTERVAL", 30)),
            }

            # Add password if provided
            redis_password = os.getenv("REDIS_PASSWORD")
            if redis_password:
                redis_config["password"] = redis_password

            self.redis_client = redis.Redis(**redis_config)

            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis at {redis_config['host']}:{redis_config['port']}")

        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Caching will be disabled.")
            self.redis_client = None
            self.enabled = False

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

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/Redis unavailable
        """
        if not self.enabled or not self.redis_client:
            return None

        try:
            cached_data = self.redis_client.get(key)
            if cached_data:
                return json.loads(cached_data)
            return None
        except Exception as e:
            logger.warning(f"Cache get failed for key {key}: {e}")
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
        if not self.enabled or not self.redis_client:
            return False

        try:
            # Serialize the value
            serialized_value = json.dumps(value, default=str)

            # Set with TTL
            result = self.redis_client.setex(key, ttl, serialized_value)
            return bool(result)
        except Exception as e:
            logger.warning(f"Cache set failed for key {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete key from cache.

        Args:
            key: Cache key to delete

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            result = self.redis_client.delete(key)
            return bool(result)
        except Exception as e:
            logger.warning(f"Cache delete failed for key {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Pattern to match (e.g., 'stream_sniper:stream:*')

        Returns:
            Number of keys deleted
        """
        if not self.enabled or not self.redis_client:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                return self.redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache pattern delete failed for pattern {pattern}: {e}")
            return 0

    def flush_all(self) -> bool:
        """
        Flush all cache entries.

        Returns:
            True if successful, False otherwise
        """
        if not self.enabled or not self.redis_client:
            return False

        try:
            # Only flush our namespace
            deleted = self.delete_pattern("stream_sniper:*")
            logger.info(f"Flushed {deleted} cache entries")
            return True
        except Exception as e:
            logger.warning(f"Cache flush failed: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics and health info.

        Returns:
            Dictionary with cache statistics
        """
        if not self.enabled or not self.redis_client:
            return {"enabled": False, "status": "disabled", "error": "Redis connection not available"}

        try:
            info = self.redis_client.info()
            our_keys = len(self.redis_client.keys("stream_sniper:*"))

            return {
                "enabled": True,
                "status": "healthy",
                "redis_version": info.get("redis_version"),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "stream_sniper_keys": our_keys,
                "uptime_in_seconds": info.get("uptime_in_seconds"),
            }
        except Exception as e:
            logger.warning(f"Failed to get cache stats: {e}")
            return {"enabled": True, "status": "unhealthy", "error": str(e)}


# Global cache instance
_cache_instance: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """
    Get the global Redis cache instance.

    Returns:
        RedisCache instance
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
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
                cache_key = cache._generate_key("stream_count", creator_id)
                cache.set(cache_key, count, ttl=1800)  # 30 minutes
            except:
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

    # Volatile data
    HEALTH_CHECK = 300  # 5 minutes
    LIVE_STATS = 60  # 1 minute
