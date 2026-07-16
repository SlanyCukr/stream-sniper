"""Domain-specific cache warm-up policy used during API startup."""

from ...database.gateways.identity.creator_table_gateway import select_creators_db
from ...database.gateways.streams.stream_table_gateway import count_streams_db
from ...logging_config import get_logger
from .cache import CacheTTL, InProcessCache

logger = get_logger(__name__)


def warm_cache(cache: InProcessCache) -> None:
    """Preload the creator list and common stream-count queries."""
    logger.info("Starting cache warming process")
    creators = select_creators_db()
    if creators:
        key = cache.generate_key("creators")
        if not cache.set(key, creators, CacheTTL.CREATORS):
            raise RuntimeError("Failed to populate creators cache")
        logger.info("Warmed creators cache with %s entries", len(creators))

    failures: list[Exception] = []
    for creator_id in (-1, 1, 2, 3):
        try:
            count = count_streams_db(creator_id)
            key = cache.generate_key("stream_count", creator_id, None, None, None, None)
            if not cache.set(key, count, CacheTTL.STREAM_COUNT):
                raise RuntimeError("Cache rejected stream count")
        except Exception as error:
            logger.exception("Skipping cache warm for creator_id=%s", creator_id)
            failures.append(error)
    if failures:
        raise ExceptionGroup("Cache warming partially failed", failures)
    logger.info("Cache warming completed")
