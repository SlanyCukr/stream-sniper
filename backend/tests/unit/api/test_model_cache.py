"""Tests for typed HTTP response-cache policy."""

from datetime import UTC, datetime
from unittest.mock import Mock, call, patch

import pytest
from fastapi import Response
from pydantic import BaseModel, RootModel

from stream_sniper.api.caching.model_cache import ModelCachePolicy


class ExamplePayload(BaseModel):
    count: int


class ExamplePayloads(RootModel[list[ExamplePayload]]):
    pass


class TimestampedPayload(BaseModel):
    created_at: datetime


@patch("stream_sniper.api.caching.model_cache.record_cache_operation")
def test_lookup_validates_cached_payload(record_operation: Mock) -> None:
    cache = Mock()
    cache.generate_key.return_value = "cache-key"
    cache.get.return_value = {"count": 3}
    response = Response()
    policy = ModelCachePolicy("example", 60, ExamplePayload)

    key, payload = policy.lookup(cache, response, 7)

    assert key == "cache-key"
    assert payload == ExamplePayload(count=3)
    assert response.headers["X-Cache"] == "HIT"
    cache.delete.assert_not_called()
    record_operation.assert_called_once_with("hit", "example")


@patch("stream_sniper.api.caching.model_cache.record_cache_operation")
def test_lookup_evicts_payload_that_fails_model_validation(record_operation: Mock) -> None:
    cache = Mock()
    cache.generate_key.return_value = "cache-key"
    cache.get.return_value = {"count": "not-an-integer"}
    response = Response()
    policy = ModelCachePolicy("example", 60, ExamplePayload)

    key, payload = policy.lookup(cache, response, 7)

    assert key == "cache-key"
    assert payload is None
    assert response.headers["X-Cache"] == "MISS"
    cache.delete.assert_called_once_with("cache-key")
    record_operation.assert_called_once_with("miss", "example")


@patch("stream_sniper.api.caching.model_cache.record_cache_operation")
def test_store_serializes_model_at_policy_ttl(record_operation: Mock) -> None:
    cache = Mock()
    response = Response()
    policy = ModelCachePolicy("example", 60, ExamplePayload)

    policy.store(cache, response, "cache-key", ExamplePayload(count=4))

    cache.set.assert_called_once_with("cache-key", {"count": 4}, 60)
    assert response.headers["X-Cache"] == "MISS"
    record_operation.assert_called_once_with("set", "example")


def test_root_model_cache_evicts_malformed_list() -> None:
    cache = Mock()
    cache.generate_key.return_value = "cache-key"
    cache.get.return_value = [{"count": 1}, {"count": "invalid"}]
    response = Response()
    policy = ModelCachePolicy("examples", 60, ExamplePayloads)

    _, payload = policy.lookup(cache, response)

    assert payload is None
    assert response.headers["X-Cache"] == "MISS"
    cache.delete.assert_called_once_with("cache-key")


def test_store_uses_json_mode_serialization() -> None:
    cache = Mock()
    response = Response()
    policy = ModelCachePolicy("timestamped", 60, TimestampedPayload)
    created_at = datetime(2026, 7, 16, 1, 2, 3, tzinfo=UTC)

    policy.store(cache, response, "cache-key", TimestampedPayload(created_at=created_at))

    cache.set.assert_called_once_with("cache-key", {"created_at": "2026-07-16T01:02:03Z"}, 60)


@patch("stream_sniper.api.caching.model_cache.record_cache_operation")
def test_record_failures_tracks_unexpected_errors(record_operation: Mock) -> None:
    policy = ModelCachePolicy("example", 60, ExamplePayload)

    with pytest.raises(RuntimeError, match="cache failed"), policy.record_failures():
        raise RuntimeError("cache failed")

    assert record_operation.call_args_list == [call("error", "example")]
