"""Unit tests for the tracking liveness heartbeat (Postgres-backed)."""

import pytest

from stream_sniper.database.gateways.tracking.tracking_heartbeat_table_gateway import (
    select_heartbeat_db,
    upsert_heartbeat_db,
)
from stream_sniper.tracking import heartbeat
from stream_sniper.tracking.status import HeartbeatState, TrackingStatus

SAMPLE_PAYLOAD = {
    "scheduler": {
        "running": True,
        "start_time": "2026-07-15T12:00:00",
        "uptime_seconds": 12.0,
        "monitor_interval": 60,
        "max_concurrent_jobs": 2,
        "max_retries": 3,
    },
    "stream_monitor": {
        "running": True,
        "check_interval": 60,
        "tracked_streamers_count": 2,
        "last_stream_states": {"alice": "live"},
    },
    "processing_queue": {
        "running": True,
        "active_jobs": 1,
        "max_concurrent_jobs": 2,
        "max_retries": 3,
        "active_job_ids": [7],
    },
}
SAMPLE = TrackingStatus.model_validate(SAMPLE_PAYLOAD)


def test_write_delegates_to_gateway(monkeypatch):
    calls = {}

    def fake_upsert(component, status):
        calls["component"] = component
        calls["status"] = status
        return True

    monkeypatch.setattr(heartbeat, "upsert_heartbeat_db", fake_upsert)

    assert heartbeat.write_heartbeat(SAMPLE) is True
    assert calls["component"] == heartbeat.HEARTBEAT_COMPONENT
    assert calls["status"] == SAMPLE.model_dump(mode="json")


def test_read_fresh_is_alive(monkeypatch):
    monkeypatch.setattr(heartbeat, "select_heartbeat_db", lambda c: (SAMPLE_PAYLOAD, 5.0))

    result = heartbeat.read_heartbeat()
    assert result.alive is True
    assert result.age_seconds == 5.0
    assert result.status is not None
    assert result.status.stream_monitor.running is True


def test_read_stale_is_not_alive(monkeypatch):
    stale_age = heartbeat.HEARTBEAT_STALE_AFTER + 10
    monkeypatch.setattr(heartbeat, "select_heartbeat_db", lambda c: (SAMPLE_PAYLOAD, stale_age))

    result = heartbeat.read_heartbeat()
    assert result.alive is False
    assert result.state is HeartbeatState.STALE


def test_read_at_threshold_is_alive(monkeypatch):
    # age exactly at the threshold is still considered alive (<=).
    monkeypatch.setattr(
        heartbeat,
        "select_heartbeat_db",
        lambda c: (SAMPLE_PAYLOAD, float(heartbeat.HEARTBEAT_STALE_AFTER)),
    )
    result = heartbeat.read_heartbeat()
    assert result.alive is True
    assert result.state is HeartbeatState.FRESH


def test_read_missing_row_returns_missing_snapshot(monkeypatch):
    monkeypatch.setattr(heartbeat, "select_heartbeat_db", lambda c: None)
    result = heartbeat.read_heartbeat()
    assert result.state is HeartbeatState.MISSING
    assert result.status is None


def test_read_propagates_database_failure(monkeypatch):
    def fail(_component):
        raise RuntimeError("database offline")

    monkeypatch.setattr(heartbeat, "select_heartbeat_db", fail)
    with pytest.raises(RuntimeError, match="database offline"):
        heartbeat.read_heartbeat()


def test_read_marks_null_status_incompatible(monkeypatch):
    monkeypatch.setattr(heartbeat, "select_heartbeat_db", lambda c: (None, 1.0))
    result = heartbeat.read_heartbeat()
    assert result.state is HeartbeatState.INCOMPATIBLE
    assert result.alive is False
    assert result.validation_error


def test_read_marks_unknown_schema_incompatible(monkeypatch):
    monkeypatch.setattr(heartbeat, "select_heartbeat_db", lambda c: ({"version": 999}, 1.0))
    result = heartbeat.read_heartbeat()
    assert result.state is HeartbeatState.INCOMPATIBLE
    assert result.status is None


def test_delete_delegates_to_gateway(monkeypatch):
    seen = {}

    def fake_delete(component):
        seen["component"] = component
        return True

    monkeypatch.setattr(heartbeat, "delete_heartbeat_db", fake_delete)
    assert heartbeat.delete_heartbeat() is True
    assert seen["component"] == heartbeat.HEARTBEAT_COMPONENT


def test_gateway_rejects_non_object_payload_on_write():
    with pytest.raises(TypeError, match="JSON object"):
        upsert_heartbeat_db("tracking", [])  # type: ignore[arg-type]


def test_gateway_rejects_non_object_payload_on_read(mock_connection_pool):
    _, _, cursor = mock_connection_pool
    cursor.fetchone.return_value = (["old", "schema"], 1.0)

    with pytest.raises(ValueError, match="JSON object"):
        select_heartbeat_db("tracking")
