"""Tracked-streamer patch contract tests."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.features.tracking.tracking_streamer_endpoints import router
from stream_sniper.api.security.auth import get_current_admin_user
from stream_sniper.api.security.rate_limiter import setup_rate_limiting
from stream_sniper.application.tracking.models import TrackedStreamer
from stream_sniper.database.core.patches import UNSET


def _row(notes: str | None) -> TrackedStreamer:
    now = datetime(2026, 7, 15, 12)
    return TrackedStreamer(
        7,
        70,
        "operator",
        "Operator",
        True,
        None,
        None,
        True,
        now,
        now,
        1,
        notes,
        "Operator",
        None,
        "admin",
    )


def _client() -> TestClient:
    app = FastAPI()
    setup_rate_limiting(app)
    app.include_router(router, prefix="/admin/tracking")
    app.dependency_overrides[get_current_admin_user] = lambda: SimpleNamespace(username="admin")
    return TestClient(app)


def test_explicit_null_clears_notes_without_touching_other_fields() -> None:
    with (
        patch(
            "stream_sniper.api.features.tracking.tracking_streamer_endpoints.select_tracked_streamer_by_id_db",
            side_effect=[_row("old note"), _row(None)],
        ),
        patch(
            "stream_sniper.api.features.tracking.tracking_streamer_endpoints.update_tracked_streamer_db",
            return_value=True,
        ) as update,
    ):
        response = _client().put("/admin/tracking/streamers/7", json={"notes": None})

    assert response.status_code == 200
    assert response.json()["notes"] is None
    update.assert_called_once_with(7, is_active=UNSET, processing_enabled=UNSET, notes=None)


def test_empty_patch_is_rejected() -> None:
    with patch(
        "stream_sniper.api.features.tracking.tracking_streamer_endpoints.select_tracked_streamer_by_id_db",
        return_value=_row("old note"),
    ):
        response = _client().put("/admin/tracking/streamers/7", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "Nothing to save — change at least one field first."


@pytest.mark.parametrize("field", ["is_active", "processing_enabled"])
def test_explicit_null_boolean_is_rejected(field: str) -> None:
    with patch("stream_sniper.api.features.tracking.tracking_streamer_endpoints.update_tracked_streamer_db") as update:
        response = _client().put("/admin/tracking/streamers/7", json={field: None})

    assert response.status_code == 422
    update.assert_not_called()
