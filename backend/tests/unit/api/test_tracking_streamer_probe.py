"""Twitch probe endpoint + collection-summary list enrichment tests."""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.features.tracking.tracking_streamer_endpoints import router
from stream_sniper.api.security.auth import get_current_admin_user
from stream_sniper.api.security.rate_limiter import setup_rate_limiting
from stream_sniper.application.tracking.models import TrackedStreamer
from stream_sniper.collector.twitch_api import TwitchConfigurationError, TwitchUpstreamError
from stream_sniper.database.gateways.streams.records import CreatorStreamSummaryRow

_ENDPOINTS = "stream_sniper.api.features.tracking.tracking_streamer_endpoints"


def _row() -> TrackedStreamer:
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
        None,
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


def _twitch(live: object = None, videos: list | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        ensure_initialized=AsyncMock(),
        get_live_stream=AsyncMock(return_value=live),
        get_archived_videos=AsyncMock(return_value=videos or []),
    )


class TestProbe:
    def test_reports_live_channel_with_vods(self) -> None:
        videos = [
            SimpleNamespace(created_at=datetime(2026, 7, 1, 10)),
            SimpleNamespace(created_at=datetime(2026, 7, 14, 20)),
        ]
        with (
            patch(f"{_ENDPOINTS}.select_tracked_streamer_by_id_db", return_value=_row()),
            patch(f"{_ENDPOINTS}.get_twitch_client", return_value=_twitch(live=object(), videos=videos)),
        ):
            response = _client().post("/admin/tracking/streamers/7/probe")

        assert response.status_code == 200
        body = response.json()
        assert body["is_live"] is True
        assert body["archive_vod_count"] == 2
        assert body["last_vod_created_at"] == "2026-07-14T20:00:00"
        assert body["checked_at"]

    def test_reports_dormant_channel(self) -> None:
        with (
            patch(f"{_ENDPOINTS}.select_tracked_streamer_by_id_db", return_value=_row()),
            patch(f"{_ENDPOINTS}.get_twitch_client", return_value=_twitch()),
        ):
            response = _client().post("/admin/tracking/streamers/7/probe")

        assert response.status_code == 200
        body = response.json()
        assert body["is_live"] is False
        assert body["archive_vod_count"] == 0
        assert body["last_vod_created_at"] is None

    def test_unknown_streamer_404s(self) -> None:
        with patch(f"{_ENDPOINTS}.select_tracked_streamer_by_id_db", return_value=None):
            response = _client().post("/admin/tracking/streamers/999/probe")

        assert response.status_code == 404

    def test_missing_twitch_config_503s(self) -> None:
        twitch = _twitch()
        twitch.ensure_initialized = AsyncMock(side_effect=TwitchConfigurationError("no creds"))
        with (
            patch(f"{_ENDPOINTS}.select_tracked_streamer_by_id_db", return_value=_row()),
            patch(f"{_ENDPOINTS}.get_twitch_client", return_value=twitch),
        ):
            response = _client().post("/admin/tracking/streamers/7/probe")

        assert response.status_code == 503

    def test_twitch_outage_502s(self) -> None:
        twitch = _twitch()
        twitch.get_archived_videos = AsyncMock(side_effect=TwitchUpstreamError("boom"))
        with (
            patch(f"{_ENDPOINTS}.select_tracked_streamer_by_id_db", return_value=_row()),
            patch(f"{_ENDPOINTS}.get_twitch_client", return_value=twitch),
        ):
            response = _client().post("/admin/tracking/streamers/7/probe")

        assert response.status_code == 502


class TestListCollectionSummary:
    def test_list_attaches_batched_summaries(self) -> None:
        summary = CreatorStreamSummaryRow(70, 12, datetime(2026, 7, 10, 18))
        with (
            patch(f"{_ENDPOINTS}.select_tracked_streamers_db", return_value=[_row()]),
            patch(f"{_ENDPOINTS}.count_tracked_streamers_db", return_value=1),
            patch(f"{_ENDPOINTS}.select_creator_stream_summaries_db", return_value=[summary]) as summaries,
        ):
            response = _client().get("/admin/tracking/streamers")

        assert response.status_code == 200
        streamer = response.json()["streamers"][0]
        assert streamer["total_streams_collected"] == 12
        assert streamer["last_collected_stream_start"] == "2026-07-10T18:00:00"
        summaries.assert_called_once_with([70])

    def test_creator_without_streams_stays_null(self) -> None:
        with (
            patch(f"{_ENDPOINTS}.select_tracked_streamers_db", return_value=[_row()]),
            patch(f"{_ENDPOINTS}.count_tracked_streamers_db", return_value=1),
            patch(f"{_ENDPOINTS}.select_creator_stream_summaries_db", return_value=[]),
        ):
            response = _client().get("/admin/tracking/streamers")

        assert response.status_code == 200
        streamer = response.json()["streamers"][0]
        assert streamer["total_streams_collected"] is None
        assert streamer["last_collected_stream_start"] is None
