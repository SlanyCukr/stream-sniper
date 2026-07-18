"""Deterministic tests for the health probe/snapshot/rendering pipeline."""

from datetime import datetime
from unittest.mock import Mock

import pytest

from stream_sniper.api.caching.cache import InProcessCache
from stream_sniper.api.config import APIConfig
from stream_sniper.api.observability.health import HealthChecker
from stream_sniper.api.observability.health_contracts import (
    HealthProbe,
    HealthStatus,
    ProbeResult,
    SystemResources,
    overall_health_status,
)
from stream_sniper.api.observability.health_renderers import (
    detailed_health_payload,
    render_prometheus,
)

_NOW = datetime(2026, 7, 15, 12, 0, 0)


def _resources() -> SystemResources:
    return SystemResources(
        cpu_percent=10.0,
        memory_percent=20.0,
        memory_available_mb=100.0,
        memory_used_mb=25.0,
        memory_total_mb=125.0,
        disk_percent=30.0,
        disk_free_gb=40.0,
        disk_total_gb=50.0,
        load_average=(1.0, 2.0, 3.0),
        uptime_seconds=60.0,
    )


def test_snapshot_runs_each_probe_once_and_renderers_reuse_it() -> None:
    calls: list[str] = []

    def healthy_probe() -> ProbeResult:
        calls.append("database")
        return ProbeResult(HealthStatus.HEALTHY, "ready", {"query_test": True})

    checker = HealthChecker(
        config=APIConfig(version="test"),
        cache=InProcessCache(),
        session=Mock(),
        probes=[HealthProbe("database", healthy_probe)],
        resource_reader=_resources,
        monotonic=Mock(side_effect=[1.0, 1.025]),
        now=lambda: _NOW,
    )

    snapshot = checker.snapshot()
    detailed = detailed_health_payload(snapshot)
    prometheus = render_prometheus(snapshot)

    assert calls == ["database"]
    assert snapshot.components["database"].response_time_ms == 25.0
    assert detailed["components"]["database"]["details"] == {"query_test": True}
    assert 'component="database"} 1' in prometheus


def test_probe_exception_is_timed_and_classified_by_registry_policy() -> None:
    def failing_probe() -> ProbeResult:
        raise RuntimeError("offline")

    checker = HealthChecker(
        config=APIConfig(),
        cache=InProcessCache(),
        session=Mock(),
        probes=[HealthProbe("database", failing_probe, HealthStatus.CRITICAL)],
        resource_reader=_resources,
        monotonic=Mock(side_effect=[4.0, 4.01]),
        now=lambda: _NOW,
    )

    component = checker.snapshot().components["database"]

    assert component.status is HealthStatus.CRITICAL
    assert component.response_time_ms == 10.0
    assert component.details == {"error": "Unexpected failure. See server logs for details."}
    assert overall_health_status({"database": component}) is HealthStatus.CRITICAL


def test_checker_closes_only_the_session_it_created(monkeypatch: pytest.MonkeyPatch) -> None:
    owned = Mock()
    borrowed = Mock()
    monkeypatch.setattr(HealthChecker, "_build_session", staticmethod(lambda: owned))

    owned_checker = HealthChecker(config=APIConfig(), cache=InProcessCache())
    borrowed_checker = HealthChecker(config=APIConfig(), cache=InProcessCache(), session=borrowed)
    owned_checker.close()
    borrowed_checker.close()

    owned.close.assert_called_once_with()
    borrowed.close.assert_not_called()


def test_explicit_empty_probe_registry_disables_default_probes() -> None:
    checker = HealthChecker(config=APIConfig(), cache=InProcessCache(), session=Mock(), probes=[])

    assert checker.probes == {}
