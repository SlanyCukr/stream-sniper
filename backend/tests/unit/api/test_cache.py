"""Unit tests for the in-process TTL cache."""

import pytest

from stream_sniper.api.caching import cache as cache_module
from stream_sniper.api.caching.cache import InProcessCache
from stream_sniper.api.observability.monitoring import (
    CacheMetrics,
    MetricsCollector,
    enter_metrics_scope,
    exit_metrics_scope,
    record_cache_operation,
)


def make_cache():
    return InProcessCache()


def test_set_get_roundtrip():
    c = make_cache()
    assert c.set("k", {"a": 1, "b": [1, 2, 3]}) is True
    assert c.get("k") == {"a": 1, "b": [1, 2, 3]}


def test_get_missing_returns_none():
    assert make_cache().get("nope") is None


def test_get_returns_isolated_copy():
    c = make_cache()
    value = {"nested": {"x": 1}}
    c.set("k", value)
    got = c.get("k")
    got["nested"]["x"] = 999
    # Mutating the returned value must not corrupt the cached copy.
    assert c.get("k") == {"nested": {"x": 1}}


def test_ttl_expiry(monkeypatch):
    c = make_cache()
    t = [1000.0]
    monkeypatch.setattr(cache_module.time, "time", lambda: t[0])

    c.set("k", "v", ttl=30)
    assert c.get("k") == "v"

    t[0] = 1031.0  # 31s later, past the 30s TTL
    assert c.get("k") is None


def test_delete():
    c = make_cache()
    c.set("k", "v")
    assert c.delete("k") is True
    assert c.delete("k") is False
    assert c.get("k") is None


def test_delete_pattern_glob():
    c = make_cache()
    c.set("stream_sniper:stream:aaa", 1)
    c.set("stream_sniper:stream:bbb", 2)
    c.set("stream_sniper:chatter:ccc", 3)

    removed = c.delete_pattern("stream_sniper:stream:*")
    assert removed == 2
    assert c.get("stream_sniper:stream:aaa") is None
    assert c.get("stream_sniper:chatter:ccc") == 3


def test_flush_all_clears_namespace():
    c = make_cache()
    c.set("stream_sniper:a:1", 1)
    c.set("stream_sniper:b:2", 2)
    assert c.flush_all() is None
    assert c.get("stream_sniper:a:1") is None


def test_set_stringifies_nonjson_via_default():
    # default=str mirrors the prior Redis-backed behavior: non-JSON-native values
    # are stringified rather than rejected.
    from datetime import datetime

    c = make_cache()
    assert c.set("k", {"when": datetime(2020, 1, 1, 12, 0, 0)}) is True
    assert c.get("k") == {"when": "2020-01-01 12:00:00"}


def test_set_circular_reference_returns_false():
    c = make_cache()
    a = {}
    a["self"] = a  # json.dumps raises ValueError on circular refs
    assert c.set("k", a) is False
    assert c.get("k") is None


def test_get_stats_reports_healthy_and_count():
    c = make_cache()
    c.set("stream_sniper:a:1", 1)
    stats = c.get_stats()
    assert stats["enabled"] is True
    assert stats["status"] == "healthy"
    assert stats["backend"] == "in-process"
    assert stats["stream_sniper_keys"] == 1


def testgenerate_key_deterministic():
    c = make_cache()
    k1 = c.generate_key("stream", 1, foo="bar")
    k2 = c.generate_key("stream", 1, foo="bar")
    k3 = c.generate_key("stream", 2, foo="bar")
    assert k1 == k2
    assert k1 != k3
    assert k1.startswith("stream_sniper:stream:")


def test_prune_on_growth(monkeypatch):
    c = make_cache()
    t = [1000.0]
    monkeypatch.setattr(cache_module.time, "time", lambda: t[0])
    monkeypatch.setattr(cache_module, "_PRUNE_THRESHOLD", 5)

    # Fill with short-TTL entries, then let them expire.
    for i in range(5):
        c.set(f"stream_sniper:x:{i}", i, ttl=10)
    t[0] = 1020.0  # all expired

    # Next set trips the prune threshold and clears the expired entries.
    c.set("stream_sniper:fresh", 1, ttl=10)
    assert len(c._store) == 1
    assert c.get("stream_sniper:fresh") == 1


def test_empty_cache_metrics_report_zero_hit_and_miss_rates():
    metrics = CacheMetrics()

    assert metrics.hit_rate == 0.0
    assert metrics.miss_rate == 0.0


def test_cache_operation_facade_rejects_unknown_operations():
    collector = MetricsCollector()
    token = enter_metrics_scope(collector)
    try:
        record_cache_operation("hit", "streams")
        record_cache_operation("miss", "streams")

        summary = collector.prune_and_summarize_metrics()["cache"]
        assert summary["total_operations"]["hits"] == 1
        assert summary["total_operations"]["misses"] == 1
        with pytest.raises(ValueError, match="Unsupported cache operation"):
            record_cache_operation("unknown", "streams")  # type: ignore[arg-type]
    finally:
        exit_metrics_scope(token)
