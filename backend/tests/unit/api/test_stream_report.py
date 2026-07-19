"""Unit tests for the stream report card + full chat-log export endpoints.

The report/export router is mounted on a minimal FastAPI app with the real rate
limiter; every gateway (and the connection pool for the streaming export) is patched
at its import path in ``stream_report_endpoints``. The protected export overrides
``get_current_user`` (the base auth dependency) like the moment review tests do.
"""

import json
from contextlib import contextmanager
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.error_boundary import UnexpectedExceptionMiddleware
from stream_sniper.api.features.streams.stream_report_endpoints import router
from stream_sniper.api.security.auth import get_current_user
from stream_sniper.api.security.rate_limiter import setup_rate_limiting
from stream_sniper.application.streams.report_models import ReportMetric, ReportMetrics, StreamReport
from stream_sniper.database.gateways.analytics.records import (
    CreatorReportRow,
    StreamMetricsRow,
    TopEmoteRow,
    TopPhraseRow,
)
from stream_sniper.database.gateways.chat.records import MessageReplayRow
from stream_sniper.database.gateways.content.records import StreamMomentRow
from stream_sniper.database.gateways.streams.records import (
    StreamComprehensiveRow,
    ViewerSampleRow,
)

_EP = "stream_sniper.api.features.streams.stream_report_endpoints"
_REPORT_QUERY = "stream_sniper.application.streams.report_query"
_EXPORT_QUERY = "stream_sniper.application.streams.export_query"


def _client() -> TestClient:
    app = FastAPI()
    app.add_middleware(UnexpectedExceptionMiddleware)
    setup_rate_limiting(app)
    app.include_router(router)
    return TestClient(app)


def _user_client() -> TestClient:
    client = _client()
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1, username="viewer", role="user", is_active=True
    )
    return client


def _miss_cache():
    cache = Mock()
    cache.generate_key = Mock(return_value="test-cache-key")
    cache.get = Mock(return_value=None)
    cache.set = Mock(return_value=True)
    return cache


# select_stream_comprehensive_db row:
# (title, start, end, thumbnail_url, message_count, nick, display_name, profile_image_url, creator_id)
_COMPREHENSIVE = StreamComprehensiveRow(
    "Test stream",
    datetime(2026, 7, 1, 18, 0, 0),
    datetime(2026, 7, 1, 20, 0, 0),
    None,
    1200,
    "streamer",
    "Streamer",
    None,
    3,
)

# select_stream_metrics_db row: (total_messages, unique_chatters, duration_seconds,
# messages_per_minute, peak_messages, peak_bucket_minute, new_chatters,
# returning_chatters, sub_messages, emote_messages)
_METRICS = StreamMetricsRow(1200, 300, 7200, 10.0, 60, "2026-07-01T19:00:00", 40, 260, 600, 100)

# select_creator_report_series_db rows (ascending by start): (stream_id, start_str,
# duration_seconds, total_messages, messages_per_minute, unique_chatters,
# new_chatters, returning_chatters, sub_messages, peak_messages)
_SERIES = [
    CreatorReportRow(5, "2026-06-01T18:00:00", 7000, 1000, 8.0, 200, 30, 170, 400, 50),
    CreatorReportRow(6, "2026-06-15T18:00:00", 7100, 1100, 12.0, 400, 50, 350, 550, 70),
    CreatorReportRow(7, "2026-07-01T18:00:00", 7200, 1200, 10.0, 300, 40, 260, 600, 60),
]

_SAMPLES = [ViewerSampleRow("2026-07-01T18:00:00", 100), ViewerSampleRow("2026-07-01T18:05:00", 200)]

# select_stream_moments_db rows (ascending by bucket): (bucket_minute, offset_seconds,
# message_count, baseline, ratio, unique_chatters, sub_share, emote_share,
# top_phrases, sample_messages, status)
_MOMENTS = [
    StreamMomentRow("2026-07-01T18:30:00", 1800, 90, 30.0, 3.0, 50, None, None, None, None, None, None, None),
    StreamMomentRow("2026-07-01T19:00:00", 3600, 120, 30.0, 4.0, 60, 0.5, 0.2, None, None, "bookmarked", None, None),
    StreamMomentRow("2026-07-01T19:30:00", 5400, 150, 30.0, 5.0, 70, None, None, None, None, "rejected", None, None),
    StreamMomentRow("2026-07-01T20:00:00", 7200, 45, 30.0, None, 20, None, None, None, None, None, None, None),
]


@contextmanager
def _report_mocks(
    comprehensive=_COMPREHENSIVE,
    metrics=_METRICS,
    samples=(),
    emotes=(),
    phrases=(),
    moments=(),
    series=(),
    cache=None,
):
    with (
        patch(f"{_EP}.get_cache", return_value=cache if cache is not None else _miss_cache()),
        patch(f"{_REPORT_QUERY}.select_stream_comprehensive_db", return_value=comprehensive) as mock_comp,
        patch(f"{_REPORT_QUERY}.select_stream_metrics_db", return_value=metrics) as mock_metrics,
        patch(f"{_REPORT_QUERY}.select_stream_viewer_samples_db", return_value=list(samples)) as mock_samples,
        patch(f"{_REPORT_QUERY}.select_stream_emotes_db", return_value=list(emotes)) as mock_emotes,
        patch(f"{_REPORT_QUERY}.select_stream_phrases_db", return_value=list(phrases)) as mock_phrases,
        patch(f"{_REPORT_QUERY}.select_stream_moments_db", return_value=list(moments)) as mock_moments,
        patch(f"{_REPORT_QUERY}.select_creator_report_series_db", return_value=list(series)) as mock_series,
    ):
        yield SimpleNamespace(
            comprehensive=mock_comp,
            metrics=mock_metrics,
            samples=mock_samples,
            emotes=mock_emotes,
            phrases=mock_phrases,
            moments=mock_moments,
            series=mock_series,
        )


class TestStreamReport:
    def test_success_full_shape(self):
        with _report_mocks(
            samples=_SAMPLES,
            emotes=[TopEmoteRow("KEKW", "bttv", "abc123", 120, 30)],
            phrases=[TopPhraseRow("gg wp", 22, 15)],
            moments=_MOMENTS,
            series=_SERIES,
        ) as mocks:
            response = _client().get("/streams/7/report")

        assert response.status_code == 200
        assert response.headers["X-Cache"] == "MISS"
        mocks.series.assert_called_once_with(3, 11)  # creator_id, lookback + 1
        assert response.json() == {
            "stream_id": 7,
            "creator_id": 3,
            "creator_nick": "streamer",
            "title": "Test stream",
            "start": "2026-07-01T18:00:00",
            "end": "2026-07-01T20:00:00",
            "duration_seconds": 7200,
            "baseline_count": 2,
            "lookback": 10,
            "metrics": {
                "messages_per_minute": {
                    "value": 10.0,
                    "delta_pct": 0.0,
                    "percentile": 50.0,
                    "baseline_median": 10.0,
                },
                "total_messages": {
                    "value": 1200.0,
                    "delta_pct": 14.3,
                    "percentile": 100.0,
                    "baseline_median": 1050.0,
                },
                "unique_chatters": {
                    "value": 300.0,
                    "delta_pct": 0.0,
                    "percentile": 50.0,
                    "baseline_median": 300.0,
                },
                "new_chatters": {
                    "value": 40.0,
                    "delta_pct": 0.0,
                    "percentile": 50.0,
                    "baseline_median": 40.0,
                },
                "returning_chatters": {
                    "value": 260.0,
                    "delta_pct": 0.0,
                    "percentile": 50.0,
                    "baseline_median": 260.0,
                },
                "sub_share": {
                    "value": 0.5,
                    "delta_pct": 11.1,
                    "percentile": 75.0,
                    "baseline_median": 0.45,
                },
                "peak_messages": {
                    "value": 60.0,
                    "delta_pct": 0.0,
                    "percentile": 50.0,
                    "baseline_median": 60.0,
                },
                "avg_viewers": {
                    "value": 150.0,
                    "delta_pct": None,
                    "percentile": None,
                    "baseline_median": None,
                },
                "peak_viewers": {
                    "value": 200.0,
                    "delta_pct": None,
                    "percentile": None,
                    "baseline_median": None,
                },
            },
            "peak_bucket_minute": "2026-07-01T19:00:00",
            "top_emote": {
                "name": "KEKW",
                "source": "bttv",
                "provider_id": "abc123",
                "usage_count": 120,
                "chatter_count": 30,
            },
            "top_phrase": {"phrase": "gg wp", "usage_count": 22, "chatter_count": 15},
            "top_moments": [
                {
                    "bucket_minute": "2026-07-01T19:00:00",
                    "offset_seconds": 3600,
                    "message_count": 120,
                    "ratio": 4.0,
                    "status": "bookmarked",
                },
                {
                    "bucket_minute": "2026-07-01T18:30:00",
                    "offset_seconds": 1800,
                    "message_count": 90,
                    "ratio": 3.0,
                    "status": None,
                },
                {
                    "bucket_minute": "2026-07-01T20:00:00",
                    "offset_seconds": 7200,
                    "message_count": 45,
                    "ratio": None,
                    "status": None,
                },
            ],
        }

    def test_404_when_stream_missing(self):
        with _report_mocks(comprehensive=None) as mocks:
            response = _client().get("/streams/999/report")

        assert response.status_code == 404
        assert response.json() == {"detail": "Stream not found"}
        mocks.series.assert_not_called()

    def test_unrolled_stream_returns_200_with_nulls(self):
        # Un-rolled-up: no stream_metrics row, no samples/emotes/phrases/moments; the
        # creator's previous streams are un-rolled too (NULL metrics columns).
        unrolled_series = [
            CreatorReportRow(5, "2026-06-01T18:00:00", None, None, None, None, None, None, None, None),
            CreatorReportRow(6, "2026-06-15T18:00:00", None, None, None, None, None, None, None, None),
        ]
        with _report_mocks(metrics=None, series=unrolled_series):
            response = _client().get("/streams/7/report")

        assert response.status_code == 200
        data = response.json()
        assert data["baseline_count"] == 0
        assert data["duration_seconds"] is None
        assert data["peak_bucket_minute"] is None
        assert data["top_emote"] is None
        assert data["top_phrase"] is None
        assert data["top_moments"] == []
        for metric in data["metrics"].values():
            assert metric == {
                "value": None,
                "delta_pct": None,
                "percentile": None,
                "baseline_median": None,
            }

    def test_single_baseline_stream_suppresses_baseline_stats(self):
        with _report_mocks(series=[_SERIES[0], _SERIES[2]]):
            response = _client().get("/streams/7/report")

        data = response.json()
        assert data["baseline_count"] == 1
        assert data["metrics"]["messages_per_minute"] == {
            "value": 10.0,
            "delta_pct": None,
            "percentile": None,
            "baseline_median": None,
        }

    def test_streams_after_this_one_excluded_from_baseline(self):
        newer = CreatorReportRow(9, "2026-07-10T18:00:00", 7000, 900, 9.0, 250, 20, 230, 450, 55)
        with _report_mocks(series=[_SERIES[0], _SERIES[2], newer]):
            response = _client().get("/streams/7/report")

        data = response.json()
        # Only stream 5 predates this one; the newer stream 9 must not enter the baseline.
        assert data["baseline_count"] == 1
        assert data["metrics"]["total_messages"]["baseline_median"] is None

    def test_lookback_forwarded_and_echoed(self):
        with _report_mocks(series=_SERIES) as mocks:
            response = _client().get("/streams/7/report?lookback=5")

        assert response.json()["lookback"] == 5
        mocks.series.assert_called_once_with(3, 6)

    def test_lookback_out_of_range_rejected(self):
        assert _client().get("/streams/7/report?lookback=1").status_code == 422
        assert _client().get("/streams/7/report?lookback=31").status_code == 422

    def test_cache_hit_skips_gateways(self):
        cached_payload = StreamReport(
            stream_id=7,
            creator_id=3,
            baseline_count=0,
            lookback=10,
            metrics=ReportMetrics(
                **{
                    name: ReportMetric()
                    for name in (
                        "messages_per_minute",
                        "total_messages",
                        "unique_chatters",
                        "new_chatters",
                        "returning_chatters",
                        "sub_share",
                        "peak_messages",
                        "avg_viewers",
                        "peak_viewers",
                    )
                }
            ),
        ).model_dump()
        cache = Mock()
        cache.generate_key = Mock(return_value="k")
        cache.get = Mock(return_value=cached_payload)
        cache.set = Mock()
        with _report_mocks(cache=cache) as mocks:
            response = _client().get("/streams/7/report")

        assert response.status_code == 200
        assert response.headers["X-Cache"] == "HIT"
        assert response.json() == cached_payload
        mocks.comprehensive.assert_not_called()
        mocks.series.assert_not_called()
        cache.set.assert_not_called()

    def test_gateway_error_returns_500(self):
        with _report_mocks() as mocks:
            mocks.comprehensive.side_effect = Exception("boom")
            response = _client().get("/streams/7/report")

        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error"}


_EXPORT_ROWS = [
    MessageReplayRow(1, "2026-07-01T18:00:00.000000", 11, "alice", "hello, world", True, "subscriber/12"),
    MessageReplayRow(2, "2026-07-01T18:00:01.500000", 12, "bob", 'say "hi"\nbye', None, None),
]


class TestStreamExport:
    def test_unauthenticated_rejected(self):
        response = _client().get("/streams/7/export")
        assert response.status_code in (401, 403)

    @patch(f"{_EXPORT_QUERY}.select_stream_comprehensive_db")
    @patch(f"{_EXPORT_QUERY}.iter_stream_message_export_db")
    def test_404_when_stream_missing(self, mock_export_rows, mock_comprehensive):
        mock_comprehensive.return_value = None

        response = _user_client().get("/streams/999/export")

        assert response.status_code == 404
        assert response.json() == {"detail": "Stream not found"}
        mock_export_rows.assert_not_called()

    @patch(f"{_EXPORT_QUERY}.select_stream_comprehensive_db")
    @patch(f"{_EXPORT_QUERY}.iter_stream_message_export_db")
    def test_ndjson_default(self, mock_export_rows, mock_comprehensive):
        mock_comprehensive.return_value = _COMPREHENSIVE
        mock_export_rows.return_value = iter(_EXPORT_ROWS)

        response = _user_client().get("/streams/7/export")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("application/x-ndjson")
        assert response.headers["content-disposition"] == 'attachment; filename="stream_7_chat.ndjson"'
        lines = response.text.splitlines()
        assert [json.loads(line) for line in lines] == [
            {
                "id": 1,
                "time": "2026-07-01T18:00:00.000000",
                "chatter_id": 11,
                "nick": "alice",
                "text": "hello, world",
                "is_subscriber": True,
                "badges": "subscriber/12",
            },
            {
                "id": 2,
                "time": "2026-07-01T18:00:01.500000",
                "chatter_id": 12,
                "nick": "bob",
                "text": 'say "hi"\nbye',
                "is_subscriber": None,
                "badges": None,
            },
        ]
        mock_export_rows.assert_called_once_with(7, None)

    @patch(f"{_EXPORT_QUERY}.select_stream_comprehensive_db")
    @patch(f"{_EXPORT_QUERY}.iter_stream_message_export_db")
    def test_csv_format(self, mock_export_rows, mock_comprehensive):
        mock_comprehensive.return_value = _COMPREHENSIVE
        mock_export_rows.return_value = iter(_EXPORT_ROWS)

        response = _user_client().get("/streams/7/export?format=csv")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/csv")
        assert response.headers["content-disposition"] == 'attachment; filename="stream_7_chat.csv"'
        assert response.text == (
            "id,time,chatter_id,nick,text,is_subscriber,badges\r\n"
            '1,2026-07-01T18:00:00.000000,11,alice,"hello, world",True,subscriber/12\r\n'
            '2,2026-07-01T18:00:01.500000,12,bob,"say ""hi""\nbye",,\r\n'
        )

    def test_invalid_format_rejected(self):
        assert _user_client().get("/streams/7/export?format=xml").status_code == 422

    @patch(f"{_EXPORT_QUERY}.select_stream_comprehensive_db")
    def test_gateway_error_returns_500(self, mock_comprehensive):
        mock_comprehensive.side_effect = Exception("boom")

        response = _user_client().get("/streams/7/export")

        assert response.status_code == 500
        assert response.json() == {"detail": "Internal server error"}


class TestSubShareRounding:
    """_sub_share carries the same 4-decimal precision contract as compare's _share."""

    def test_rounds_to_four_places(self):
        from stream_sniper.application.streams.report_query import _sub_share

        assert _sub_share(1, 3) == 0.3333

    def test_nullable_unknown_contract(self):
        from stream_sniper.application.streams.report_query import _sub_share

        assert _sub_share(None, 100) is None
        assert _sub_share(10, None) is None
        assert _sub_share(10, 0) is None
