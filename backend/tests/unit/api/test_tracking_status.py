"""API contracts for typed tracking status and heartbeat provenance."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.config import APIConfig
from stream_sniper.api.features.tracking.tracking_service_endpoints import router
from stream_sniper.api.security.auth import get_current_admin_user
from stream_sniper.api.security.rate_limiter import setup_rate_limiting
from stream_sniper.tracking.status import (
    HeartbeatSnapshot,
    HeartbeatState,
    TrackingStatus,
)

STATUS = TrackingStatus.model_validate(
    {
        "scheduler": {
            "running": True,
            "start_time": "2026-07-15T12:00:00",
            "uptime_seconds": 30.0,
            "monitor_interval": 60,
            "max_concurrent_jobs": 2,
            "max_retries": 3,
        },
        "stream_monitor": {
            "running": True,
            "check_interval": 60,
            "tracked_streamers_count": 1,
            "last_stream_states": {"alice": "live"},
            "successful_checks": 0,
            "failed_checks": 1,
            "unknown_checks": 0,
            "degraded": True,
            "last_cycle_completed_at": "2026-07-15T12:00:00+00:00",
            "last_successful_cycle": None,
        },
        "processing_queue": {
            "running": True,
            "active_jobs": 1,
            "max_concurrent_jobs": 2,
            "max_retries": 3,
            "active_job_ids": [7],
        },
    }
)


@pytest.fixture
def client():
    app = FastAPI()
    app.state.config = APIConfig()
    app.state.runtime = SimpleNamespace()
    setup_rate_limiting(app)
    app.include_router(router, prefix="/admin/tracking")
    app.dependency_overrides[get_current_admin_user] = lambda: SimpleNamespace(
        id=1,
        username="admin",
        role="admin",
    )
    with TestClient(app) as test_client:
        yield test_client


def test_service_status_uses_fresh_validated_heartbeat(client):
    heartbeat = HeartbeatSnapshot(
        state=HeartbeatState.FRESH,
        status=STATUS,
        age_seconds=2.0,
        alive=True,
    )
    with patch(
        "stream_sniper.api.features.tracking.tracking_service_endpoints.read_heartbeat",
        return_value=heartbeat,
    ):
        response = client.get("/admin/tracking/service/status")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "heartbeat"
    assert body["heartbeat"]["state"] == "fresh"
    assert body["stream_monitor"]["last_stream_states"] == {"alice": "live"}
    assert body["stream_monitor"]["degraded"] is True
    assert body["stream_monitor"]["failed_checks"] == 1


def test_tracking_stats_distinguishes_running_from_degraded(client):
    heartbeat = HeartbeatSnapshot(
        state=HeartbeatState.FRESH,
        status=STATUS,
        age_seconds=2.0,
        alive=True,
    )
    with (
        patch(
            "stream_sniper.api.features.tracking.tracking_service_endpoints.read_heartbeat",
            return_value=heartbeat,
        ),
        patch(
            "stream_sniper.api.features.tracking.tracking_service_endpoints.count_tracked_streamers_db",
            side_effect=[2, 2, 1],
        ),
        patch(
            "stream_sniper.api.features.tracking.tracking_service_endpoints.select_processing_stats_db",
            return_value={"pending": 0, "failed": 0},
        ),
    ):
        response = client.get("/admin/tracking/stats")

    assert response.status_code == 200
    system = response.json()["system_status"]
    assert system["monitoring_active"] is True
    assert system["monitoring_degraded"] is True


def test_service_status_exposes_incompatible_heartbeat(client):
    heartbeat = HeartbeatSnapshot(
        state=HeartbeatState.INCOMPATIBLE,
        age_seconds=2.0,
        validation_error="schema mismatch",
    )
    with patch(
        "stream_sniper.api.features.tracking.tracking_service_endpoints.read_heartbeat",
        return_value=heartbeat,
    ):
        response = client.get("/admin/tracking/service/status")

    assert response.status_code == 200
    body = response.json()
    assert body["heartbeat"]["state"] == "incompatible"
    assert body["heartbeat"]["validation_error"] == "schema mismatch"
    assert body["source"] == "none"
