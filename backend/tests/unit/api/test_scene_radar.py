"""Unit tests for the live Moment Radar endpoint and its pure assembly.

GET /scene/radar. The gateway is monkeypatched; the router is mounted on a fresh app. The
velocity math (zero-fill, median baseline, ratio, spike flag, ordering, partial-minute
exclusion) is covered directly against ``build_radar`` — the index-shaped SQL is verified
against a scratch Postgres in the gateway step, not here.
"""

from datetime import datetime
from unittest.mock import Mock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.error_boundary import UnexpectedExceptionMiddleware
from stream_sniper.api.features.content.scene_radar_endpoints import build_radar, router
from stream_sniper.api.security.rate_limiter import setup_rate_limiting
from stream_sniper.database.gateways.content.scene_radar_gateway import LiveStreamRow, MinuteCountRow

# Fixed "now" mid-minute: floor is 12:34, last COMPLETED minute is 12:33.
NOW = datetime(2026, 7, 18, 12, 34, 30)
LAST_COMPLETED = datetime(2026, 7, 18, 12, 33)


def _build_app():
    app = FastAPI()
    setup_rate_limiting(app)
    app.add_middleware(UnexpectedExceptionMiddleware)
    app.include_router(router)
    return app


app = _build_app()


def _miss_cache():
    cache = Mock()
    cache.generate_key = Mock(side_effect=lambda *a, **k: "key:" + ":".join(str(x) for x in a))
    cache.get = Mock(return_value=None)
    cache.set = Mock(return_value=True)
    cache.delete = Mock(return_value=True)
    return cache


def _live(stream_id=1, creator_id=10):
    return LiveStreamRow(
        stream_id=stream_id,
        creator_id=creator_id,
        creator_nick=f"nick{stream_id}",
        creator_display_name=f"Display {stream_id}",
        profile_image_url="http://img/x.png",
        stream_title="playing something",
        started_at="2026-07-18T11:00:00",
    )


def _minute(dt: datetime, messages: int, unique: int, stream_id=1):
    return MinuteCountRow(
        stream_id=stream_id,
        minute=dt.strftime("%Y-%m-%dT%H:%M:%S"),
        messages=messages,
        unique_chatters=unique,
    )


def _m(offset_from_last: int) -> datetime:
    """A completed-minute timestamp, ``offset_from_last`` minutes before the last completed minute."""
    return datetime(2026, 7, 18, 12, 33 - offset_from_last)


class TestBuildRadar:
    def test_empty_when_no_live_streams(self):
        radar = build_radar([], [], NOW)
        assert radar.generated_at == "2026-07-18T12:34:30"
        assert radar.channels == []

    def test_zero_fill_and_series_shape(self):
        # Only two minutes carry data; the rest of the 15-minute window must zero-fill.
        rows = [_minute(LAST_COMPLETED, 5, 4), _minute(_m(3), 2, 2)]
        radar = build_radar([_live()], rows, NOW)
        channel = radar.channels[0]

        assert len(channel.minutes) == 15
        # Ascending, ending at the last completed minute.
        assert channel.minutes[0].minute == "2026-07-18T12:19:00"
        assert channel.minutes[-1].minute == "2026-07-18T12:33:00"
        # Zero-filled silent minutes.
        assert channel.minutes[1].messages == 0
        # The two seeded minutes appear at the right slots (12:30 is offset 3, 12:33 is last).
        by_minute = {m.minute: m.messages for m in channel.minutes}
        assert by_minute["2026-07-18T12:30:00"] == 2
        assert by_minute["2026-07-18T12:33:00"] == 5

    def test_partial_current_minute_excluded(self):
        # A row at the CURRENT in-progress minute (12:34) must never enter the series or last-minute.
        rows = [_minute(datetime(2026, 7, 18, 12, 34), 999, 50), _minute(LAST_COMPLETED, 7, 5)]
        radar = build_radar([_live()], rows, NOW)
        channel = radar.channels[0]

        assert channel.messages_last_minute == 7
        assert channel.unique_chatters_last_minute == 5
        assert all(m.minute != "2026-07-18T12:34:00" for m in channel.minutes)
        assert 999 not in [m.messages for m in channel.minutes]

    def test_baseline_null_when_fewer_than_three_nonzero_history(self):
        # Two nonzero history minutes + a busy last minute -> baseline/ratio null (needs >= 3),
        # but the burst still spikes via the absolute floor (40 >= MIN_ABSOLUTE), matching the
        # persisted-moment detector's zero-baseline behavior.
        rows = [_minute(_m(1), 4, 3), _minute(_m(2), 4, 3), _minute(LAST_COMPLETED, 40, 20)]
        channel = build_radar([_live()], rows, NOW).channels[0]

        assert channel.baseline_per_minute is None
        assert channel.ratio is None
        assert channel.spiking is True

    def test_cold_start_burst_spikes_via_absolute_floor(self):
        # All-zero history, then a 50-message burst: moments.py would persist this (baseline 0
        # -> threshold max(0, MIN_ABSOLUTE)); the radar must light up too. ratio stays null.
        rows = [_minute(LAST_COMPLETED, 50, 25)]
        channel = build_radar([_live()], rows, NOW).channels[0]

        assert channel.baseline_per_minute is None
        assert channel.ratio is None
        assert channel.spiking is True

    def test_cold_start_quiet_minute_not_spiking(self):
        # No baseline AND below the absolute floor -> not spiking.
        rows = [_minute(LAST_COMPLETED, 14, 8)]
        channel = build_radar([_live()], rows, NOW).channels[0]
        assert channel.spiking is False

    def test_sparse_history_gets_nonzero_median_baseline(self):
        # 4 active minutes among 14 (eligible: >= 3 nonzero) -> the baseline is the median of
        # the NONZERO minutes (10), not of the zero-filled window (which would be 0 and would
        # silently disable the ratio for intermittently active streams).
        history = [_minute(_m(offset), 10, 5) for offset in (2, 5, 8, 11)]
        rows = [*history, _minute(LAST_COMPLETED, 45, 18)]
        channel = build_radar([_live()], rows, NOW).channels[0]

        assert channel.baseline_per_minute == 10.0
        assert channel.ratio == 4.5
        assert channel.spiking is True

    def test_median_baseline_and_ratio(self):
        # History (excluding last completed): three minutes of 4, 6, 8 -> median 6.0 over the
        # zero-filled 14-minute window? No: 11 zeros + [4,6,8] -> median is 0. Use enough nonzero
        # minutes that the median is meaningful.
        history = [_minute(_m(offset), 10, 5) for offset in range(1, 9)]  # 8 minutes of 10
        rows = [*history, _minute(LAST_COMPLETED, 30, 12)]
        channel = build_radar([_live()], rows, NOW).channels[0]

        assert channel.baseline_per_minute == 10.0
        assert channel.ratio == 3.0
        # ratio 3.0 >= 3.0 and 30 >= 15 -> spiking.
        assert channel.spiking is True

    def test_ratio_rounded_two_dp(self):
        history = [_minute(_m(offset), 7, 4) for offset in range(1, 9)]  # median 7
        rows = [*history, _minute(LAST_COMPLETED, 20, 10)]
        channel = build_radar([_live()], rows, NOW).channels[0]
        assert channel.baseline_per_minute == 7.0
        assert channel.ratio == round(20 / 7, 2) == 2.86

    def test_not_spiking_below_absolute_floor(self):
        # ratio would be high, but messages_last_minute < MIN_ABSOLUTE (15) -> not spiking.
        history = [_minute(_m(offset), 1, 1) for offset in range(1, 9)]  # median 1
        rows = [*history, _minute(LAST_COMPLETED, 10, 6)]  # ratio 10 but only 10 msgs
        channel = build_radar([_live()], rows, NOW).channels[0]
        assert channel.ratio == 10.0
        assert channel.messages_last_minute == 10
        assert channel.spiking is False

    def test_ordering_spiking_then_volume_then_id(self):
        spiking_hist = [_minute(_m(o), 5, 3, stream_id=3) for o in range(1, 9)]
        spiking = [*spiking_hist, _minute(LAST_COMPLETED, 30, 12, stream_id=3)]  # ratio 6, spiking
        busy = [_minute(LAST_COMPLETED, 25, 10, stream_id=1)]  # cold-start burst -> floor-spiking
        quiet = [_minute(LAST_COMPLETED, 5, 2, stream_id=2)]  # below floor, not spiking
        radar = build_radar(
            [_live(1), _live(2), _live(3)],
            [*busy, *quiet, *spiking],
            NOW,
        )
        # Both spiking channels first, busiest last-minute first among them; quiet channel last.
        assert [c.stream_id for c in radar.channels] == [3, 1, 2]
        assert radar.channels[0].spiking is True
        assert radar.channels[1].spiking is True  # floor-fired despite null baseline/ratio

    def test_ordering_stream_id_tiebreak(self):
        # Two non-spiking channels with equal last-minute volume -> lower stream_id first.
        rows = [_minute(LAST_COMPLETED, 8, 4, stream_id=5), _minute(LAST_COMPLETED, 8, 4, stream_id=2)]
        radar = build_radar([_live(5), _live(2)], rows, NOW)
        assert [c.stream_id for c in radar.channels] == [2, 5]


class TestRadarEndpoint:
    @patch("stream_sniper.api.features.content.scene_radar_endpoints.get_cache")
    @patch("stream_sniper.api.features.content.scene_radar_endpoints.select_live_chat_velocity_db")
    def test_empty_returns_200_not_404(self, mock_gw, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = ([], [])

        with TestClient(app) as client:
            resp = client.get("/scene/radar")

        assert resp.status_code == 200
        data = resp.json()
        assert data["channels"] == []
        assert isinstance(data["generated_at"], str)

    @patch("stream_sniper.api.features.content.scene_radar_endpoints.get_cache")
    @patch("stream_sniper.api.features.content.scene_radar_endpoints.select_live_chat_velocity_db")
    def test_shapes_channel(self, mock_gw, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_gw.return_value = ([_live()], [])

        with TestClient(app) as client:
            resp = client.get("/scene/radar")

        assert resp.status_code == 200
        channel = resp.json()["channels"][0]
        assert channel["stream_id"] == 1
        assert channel["creator_nick"] == "nick1"
        assert channel["messages_last_minute"] == 0
        assert channel["baseline_per_minute"] is None
        assert channel["ratio"] is None
        assert channel["spiking"] is False
        assert len(channel["minutes"]) == 15

    @patch("stream_sniper.api.features.content.scene_radar_endpoints.get_cache")
    @patch("stream_sniper.api.features.content.scene_radar_endpoints.select_live_chat_velocity_db")
    def test_null_metadata_survives(self, mock_gw, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        row = _live()._replace(profile_image_url=None, stream_title=None, started_at=None)
        mock_gw.return_value = ([row], [])

        with TestClient(app) as client:
            resp = client.get("/scene/radar")

        channel = resp.json()["channels"][0]
        assert channel["profile_image_url"] is None
        assert channel["stream_title"] is None
        assert channel["started_at"] is None

    @patch("stream_sniper.api.features.content.scene_radar_endpoints.get_cache")
    @patch("stream_sniper.api.features.content.scene_radar_endpoints.select_live_chat_velocity_db")
    def test_gateway_error_returns_500(self, mock_gw, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_gw.side_effect = Exception("db down")

        with TestClient(app) as client:
            resp = client.get("/scene/radar")

        assert resp.status_code == 500
        assert resp.json()["detail"] == "Internal server error"
