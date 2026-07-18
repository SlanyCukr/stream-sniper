"""Typed response-model caching policy for HTTP read endpoints."""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass

from fastapi import HTTPException, Response
from pydantic import BaseModel, ValidationError

from ...logging_config import get_logger
from ..observability.monitoring import record_cache_operation
from .cache import InProcessCache

logger = get_logger(__name__)


@contextmanager
def record_cache_failures(prefix: str) -> Iterator[None]:
    """Record unexpected cache-backed operation failures without translating them."""
    try:
        yield
    except HTTPException:
        raise
    except Exception:
        record_cache_operation("error", prefix)
        raise


@dataclass(frozen=True)
class ModelCachePolicy[ModelT: BaseModel]:
    """Own cache keys, TTL, validation, metrics, and HTTP hit/miss headers.

    Use direct cache access only when an endpoint coordinates multiple entries
    or stores a non-model payload whose lifecycle cannot follow this policy.
    """

    prefix: str
    ttl: int
    model_type: type[ModelT]

    def lookup(self, cache: InProcessCache, response: Response, *key_parts: object) -> tuple[str, ModelT | None]:
        key = cache.generate_key(self.prefix, *key_parts)
        value = cache.get(key)
        if value is not None:
            try:
                model = self.model_type.model_validate(value)
            except ValidationError:
                logger.warning("Evicting invalid cached value for key %s", key)
                cache.delete(key)
            else:
                response.headers["X-Cache"] = "HIT"
                record_cache_operation("hit", self.prefix)
                return key, model
        response.headers["X-Cache"] = "MISS"
        record_cache_operation("miss", self.prefix)
        return key, None

    def store(self, cache: InProcessCache, response: Response, key: str, value: ModelT) -> None:
        cache.set(key, value.model_dump(mode="json"), self.ttl)
        response.headers["X-Cache"] = "MISS"
        record_cache_operation("set", self.prefix)

    @contextmanager
    def record_failures(self) -> Iterator[None]:
        with record_cache_failures(self.prefix):
            yield
