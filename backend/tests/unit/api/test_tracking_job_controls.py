"""API contracts for durable processing-job cancellation and retry."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.features.tracking.tracking_job_endpoints import router
from stream_sniper.api.security.auth import get_current_admin_user
from stream_sniper.api.security.rate_limiter import setup_rate_limiting
from stream_sniper.application.tracking.models import ProcessingJob


def _job(status: str) -> ProcessingJob:
    now = datetime(2026, 7, 15, 12)
    return ProcessingJob(7, 1, 999, status, now, None, None, 0, now, now, "alice", "Alice", None, None)


def _client() -> TestClient:
    app = FastAPI()
    setup_rate_limiting(app)
    app.include_router(router, prefix="/admin/tracking")
    app.dependency_overrides[get_current_admin_user] = lambda: SimpleNamespace(username="admin")
    return TestClient(app)


def test_cancel_persists_request_without_api_process_scheduler() -> None:
    with (
        patch(
            "stream_sniper.application.tracking.job_admin.select_processing_job_by_id_db",
            return_value=_job("in_progress"),
        ),
        patch(
            "stream_sniper.application.tracking.job_admin.request_processing_job_cancellation_db",
            return_value=True,
        ) as request_cancel,
    ):
        response = _client().post("/admin/tracking/jobs/7/cancel")

    assert response.status_code == 200
    assert response.json() == {"message": "Job cancellation requested"}
    request_cancel.assert_called_once_with(7)


def test_retry_rejects_running_job_before_transition() -> None:
    with (
        patch(
            "stream_sniper.application.tracking.job_admin.select_processing_job_by_id_db",
            return_value=_job("in_progress"),
        ),
        patch("stream_sniper.application.tracking.job_admin.retry_failed_processing_job_db") as retry,
    ):
        response = _client().post("/admin/tracking/jobs/7/retry")

    assert response.status_code == 409
    retry.assert_not_called()


def test_retry_uses_atomic_failed_transition() -> None:
    with (
        patch(
            "stream_sniper.application.tracking.job_admin.select_processing_job_by_id_db",
            return_value=_job("failed"),
        ),
        patch(
            "stream_sniper.application.tracking.job_admin.retry_failed_processing_job_db",
            return_value=True,
        ) as retry,
    ):
        response = _client().post("/admin/tracking/jobs/7/retry")

    assert response.status_code == 200
    retry.assert_called_once_with(7)
