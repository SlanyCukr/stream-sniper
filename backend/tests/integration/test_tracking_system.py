"""Tracer tests across tracking monitor, queue, scheduler, and gateway seams."""

import asyncio
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import pytest

from stream_sniper.application.tracking.models import (
    ProcessingJob,
    TrackedStreamer,
)
from stream_sniper.collector.twitch_api import TwitchUpstreamError
from stream_sniper.database.core.connection_pool import enter_pool_scope, exit_pool_scope, get_active_pool
from stream_sniper.database.gateways.tracking.processing_jobs_table_gateway import (
    JOB_STATUS_PENDING,
    ClaimedProcessingJob,
    claim_processing_jobs_db,
    enqueue_processing_job_db,
    request_processing_job_cancellation_db,
)
from stream_sniper.database.gateways.tracking.tracked_streamers_table_gateway import (
    select_active_tracked_streamers_db,
)
from stream_sniper.tracking.processing_queue import ActiveProcessingJob, ProcessingQueue
from stream_sniper.tracking.scheduler import TrackingScheduler
from stream_sniper.tracking.status import StreamObservation
from stream_sniper.tracking.stream_monitor import StreamMonitor

NOW = datetime(2026, 7, 15, 12, 0)


def _streamer_row(row_id: int = 1) -> TrackedStreamer:
    return TrackedStreamer(
        row_id,
        2,
        f"streamer{row_id}",
        f"Streamer {row_id}",
        True,
        None,
        None,
        True,
        NOW,
        NOW,
        1,
        None,
        f"Streamer {row_id}",
        None,
        "admin",
    )


def _job_row() -> ProcessingJob:
    return ProcessingJob(
        7,
        1,
        999,
        JOB_STATUS_PENDING,
        None,
        None,
        None,
        0,
        NOW,
        NOW,
        "streamer1",
        "Streamer 1",
        "Archived stream",
        NOW,
    )


class TestTrackingSystem:
    """Test suite for the tracking system components."""

    @pytest.fixture
    def mock_twitch_api(self):
        """Mock Twitch API for testing."""
        with patch("stream_sniper.tracking.stream_monitor.TwitchAPI") as mock_api:
            mock_instance = Mock()
            mock_api.return_value = mock_instance
            # Async TwitchAPI methods must be AsyncMocks so `await` works
            mock_instance._initialize_client = AsyncMock()
            mock_instance.ensure_initialized = AsyncMock()
            mock_instance.get_live_stream = AsyncMock(return_value=None)
            mock_instance.get_archived_videos = AsyncMock(return_value=[])
            mock_instance.close = AsyncMock()
            yield mock_instance

    @pytest.fixture
    def mock_database(self):
        """Mock database operations for testing."""
        # All table gateways acquire connections via the decorators module's
        # get_active_pool (the gateway modules themselves don't import get_active_pool).
        with patch("stream_sniper.database.core.decorators.get_active_pool"):
            yield

    def test_active_streamer_read_exhausts_page_boundary(self, monkeypatch):
        """The all-active contract must not silently stop at the old 1000-row cap."""
        pages = [
            [_streamer_row(index) for index in range(1, 501)],
            [_streamer_row(index) for index in range(501, 1001)],
            [_streamer_row(1001)],
        ]
        select_page = Mock(side_effect=pages)
        monkeypatch.setattr(
            "stream_sniper.database.gateways.tracking.tracked_streamers_table_gateway.select_tracked_streamers_db",
            select_page,
        )

        rows = select_active_tracked_streamers_db()

        assert len(rows) == 1001
        assert [call.kwargs["offset"] for call in select_page.call_args_list] == [0, 500, 1000]

    @pytest.mark.asyncio
    async def test_processing_job_reaches_completed_state(self, monkeypatch):
        """One claimed job runs one VOD and reaches the terminal completed transition."""
        queue = ProcessingQueue(max_concurrent_jobs=1)
        runner = AsyncMock(return_value=SimpleNamespace(twitch_vod_id=999))
        completed = Mock(return_value=True)
        failed = Mock(return_value=True)
        monkeypatch.setattr(
            "stream_sniper.tracking.processing_queue.complete_processing_job_and_advance_streamer_db",
            completed,
        )
        monkeypatch.setattr(
            "stream_sniper.tracking.processing_queue.processing_job_cancellation_requested_db",
            Mock(return_value=False),
        )
        monkeypatch.setattr("stream_sniper.tracking.processing_queue.fail_processing_job_db", failed)
        monkeypatch.setattr("stream_sniper.tracking.processing_queue.run_vod_job", runner)
        await queue._process_job(ClaimedProcessingJob(_job_row(), "lease-token"))

        runner.assert_awaited_once_with("streamer1", 999)
        completed.assert_called_once_with(7, "lease-token")
        failed.assert_not_called()

    @pytest.mark.asyncio
    async def test_migrated_postgres_tracking_tracer(self, db_cursor, mock_twitch_api, monkeypatch):
        """Drive monitor and queue transitions through the migrated gateway schema."""
        db_cursor.execute(
            "INSERT INTO users (username, email, password_hash, role) "
            "VALUES ('admin', 'admin@example.com', 'hash', 'admin') RETURNING id"
        )
        user_id = db_cursor.fetchone()[0]
        db_cursor.execute(
            "INSERT INTO creator (nick, display_name, profile_image_url, twitch_id) "
            "VALUES ('tracer', 'Tracer', '', 123) RETURNING id"
        )
        creator_id = db_cursor.fetchone()[0]
        db_cursor.execute(
            "INSERT INTO tracked_streamers "
            "(creator_id, twitch_username, display_name, created_by, is_active, processing_enabled) "
            "VALUES (%s, 'tracer', 'Tracer', %s, true, true) RETURNING id",
            (creator_id, user_id),
        )
        tracked_streamer_id = db_cursor.fetchone()[0]
        db_cursor.connection.commit()

        streamer = select_active_tracked_streamers_db()[0]
        monitor = StreamMonitor(check_interval=60)
        monitor._last_stream_states[streamer.twitch_username] = StreamObservation.LIVE
        mock_twitch_api.get_live_stream.return_value = None
        mock_twitch_api.get_archived_videos.return_value = [SimpleNamespace(twitch_vod_id="999")]
        await monitor._check_single_stream(streamer)

        claimed = claim_processing_jobs_db(
            limit=1,
            max_retries=3,
            worker_token="tracer-token",
        )
        assert len(claimed) == 1
        assert claimed[0].job.tracked_streamer_id == tracked_streamer_id
        assert claimed[0].job.twitch_vod_id == 999
        job_id = claimed[0].job.id
        monkeypatch.setattr(
            "stream_sniper.tracking.processing_queue.run_vod_job",
            AsyncMock(return_value=SimpleNamespace(twitch_vod_id=999)),
        )
        await ProcessingQueue(max_concurrent_jobs=1)._process_job(claimed[0])

        db_cursor.execute(
            "SELECT status FROM processing_jobs WHERE id = %s",
            (job_id,),
        )
        assert db_cursor.fetchone() == ("completed",)
        db_cursor.execute(
            "SELECT last_processed_vod_id FROM tracked_streamers WHERE id = %s",
            (tracked_streamer_id,),
        )
        assert db_cursor.fetchone() == (999,)

    @pytest.mark.asyncio
    async def test_migrated_postgres_cancellation_reaches_terminal_state(self, db_cursor, monkeypatch):
        """Persist, observe, and finish one leased cancellation through real gateways."""
        db_cursor.execute(
            "INSERT INTO users (username, email, password_hash, role) "
            "VALUES ('cancel-admin', 'cancel@example.com', 'hash', 'admin') RETURNING id"
        )
        user_id = db_cursor.fetchone()[0]
        db_cursor.execute(
            "INSERT INTO creator (nick, display_name, profile_image_url, twitch_id) "
            "VALUES ('cancel-tracer', 'Cancel Tracer', '', 125) RETURNING id"
        )
        creator_id = db_cursor.fetchone()[0]
        db_cursor.execute(
            "INSERT INTO tracked_streamers "
            "(creator_id, twitch_username, display_name, created_by, is_active, processing_enabled) "
            "VALUES (%s, 'cancel-tracer', 'Cancel Tracer', %s, true, true) RETURNING id",
            (creator_id, user_id),
        )
        tracked_streamer_id = db_cursor.fetchone()[0]
        db_cursor.connection.commit()

        job_id = enqueue_processing_job_db(tracked_streamer_id, 1002)
        assert job_id is not None
        claimed = claim_processing_jobs_db(limit=1, max_retries=3, worker_token="cancel-token")
        assert [item.job.id for item in claimed] == [job_id]

        runner_started = asyncio.Event()

        async def wait_for_cancellation(_username, _vod_id):
            runner_started.set()
            await asyncio.Event().wait()

        monkeypatch.setattr("stream_sniper.tracking.processing_queue.run_vod_job", wait_for_cancellation)
        queue = ProcessingQueue(max_concurrent_jobs=1, max_retries=3)
        task = asyncio.create_task(queue._process_job(claimed[0]))
        queue._active_jobs[job_id] = ActiveProcessingJob(claimed[0], task)
        await runner_started.wait()

        assert request_processing_job_cancellation_db(job_id) is True
        await queue._cancel_requested_jobs()
        assert await task == "cancelled"

        db_cursor.execute(
            "SELECT status, error_message, retry_count, worker_token, cancellation_requested_at "
            "FROM processing_jobs WHERE id = %s",
            (job_id,),
        )
        assert db_cursor.fetchone() == ("failed", "Job was cancelled", 3, None, None)

    def test_concurrent_enqueue_creates_one_job_identity(self, db_cursor):
        db_cursor.execute(
            "INSERT INTO users (username, email, password_hash, role) "
            "VALUES ('enqueue-admin', 'enqueue@example.com', 'hash', 'admin') RETURNING id"
        )
        user_id = db_cursor.fetchone()[0]
        db_cursor.execute(
            "INSERT INTO creator (nick, display_name, profile_image_url, twitch_id) "
            "VALUES ('enqueue-tracer', 'Enqueue Tracer', '', 124) RETURNING id"
        )
        creator_id = db_cursor.fetchone()[0]
        db_cursor.execute(
            "INSERT INTO tracked_streamers "
            "(creator_id, twitch_username, display_name, created_by, is_active, processing_enabled) "
            "VALUES (%s, 'enqueue-tracer', 'Enqueue Tracer', %s, true, true) RETURNING id",
            (creator_id, user_id),
        )
        tracked_streamer_id = db_cursor.fetchone()[0]
        db_cursor.connection.commit()

        start = threading.Barrier(2)
        integration_pool = get_active_pool()

        def enqueue() -> int | None:
            token = enter_pool_scope(integration_pool)
            try:
                start.wait()
                return enqueue_processing_job_db(tracked_streamer_id, 1001)
            finally:
                exit_pool_scope(token)

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(lambda _: enqueue(), range(2)))

        assert sum(result is not None for result in results) == 1
        db_cursor.execute(
            "SELECT COUNT(*) FROM processing_jobs WHERE tracked_streamer_id = %s AND twitch_vod_id = 1001",
            (tracked_streamer_id,),
        )
        assert db_cursor.fetchone() == (1,)

    @pytest.mark.asyncio
    async def test_stream_monitor_initialization(self, mock_twitch_api):
        """Test stream monitor initialization."""
        monitor = StreamMonitor(check_interval=60)

        # Test initialization
        await monitor.initialize()

        # Verify Twitch API was initialized (idempotently)
        mock_twitch_api.ensure_initialized.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stream_monitor_status_check(self, mock_twitch_api):
        """Test stream monitor status checking."""
        monitor = StreamMonitor(check_interval=60)
        await monitor.initialize()

        # Mock stream info response (monitor awaits the async variant)
        mock_twitch_api.get_live_stream.return_value = None  # Stream offline

        # Test status check
        status = await monitor.check_streamer_now("teststreamer")

        assert status.twitch_username == "teststreamer"
        assert status.state is StreamObservation.OFFLINE
        assert status.is_live is False
        assert status.last_checked is not None

    @pytest.mark.asyncio
    async def test_stream_monitor_status_error_is_unknown(self, mock_twitch_api):
        monitor = StreamMonitor(check_interval=60)
        mock_twitch_api.get_live_stream.side_effect = TwitchUpstreamError("Twitch unavailable")

        status = await monitor.check_streamer_now("teststreamer")

        assert status.state is StreamObservation.UNKNOWN
        assert status.error == "Twitch unavailable"

    @pytest.mark.asyncio
    async def test_processing_queue_initialization(self):
        """Test processing queue initialization."""
        queue = ProcessingQueue(max_concurrent_jobs=2, max_retries=3)

        # Test queue status
        status = queue.get_queue_status()
        assert status.max_concurrent_jobs == 2
        assert status.max_retries == 3
        assert status.active_jobs == 0

    @pytest.mark.asyncio
    async def test_tracking_scheduler_initialization(self, mock_twitch_api):
        """Test tracking scheduler initialization."""
        scheduler = TrackingScheduler(monitor_interval=60, max_concurrent_jobs=2, max_retries=3)

        # Test scheduler status
        status = scheduler.get_status()
        assert status.scheduler.monitor_interval == 60
        assert status.scheduler.max_concurrent_jobs == 2
        assert status.scheduler.max_retries == 3
        assert status.scheduler.running is False

    @pytest.mark.asyncio
    async def test_live_then_error_preserves_state_and_skips_end_transition(self, mock_twitch_api, monkeypatch):
        monitor = StreamMonitor(check_interval=60)
        streamer = _streamer_row()
        monitor._last_stream_states[streamer.twitch_username] = StreamObservation.LIVE
        queue_stream = AsyncMock()
        monkeypatch.setattr(monitor, "_queue_stream_for_processing", queue_stream)
        monkeypatch.setattr(
            "stream_sniper.tracking.stream_monitor.update_tracked_streamer_check_time_db",
            Mock(return_value=True),
        )
        mock_twitch_api.get_live_stream.side_effect = TwitchUpstreamError("temporary Twitch failure")

        await monitor._check_single_stream(streamer)

        assert monitor._last_stream_states[streamer.twitch_username] is StreamObservation.LIVE
        queue_stream.assert_not_awaited()

        mock_twitch_api.get_live_stream.side_effect = None
        mock_twitch_api.get_live_stream.return_value = None
        await monitor._check_single_stream(streamer)
        queue_stream.assert_awaited_once_with(streamer.id, streamer.twitch_username)

    def test_api_endpoint_structure(self):
        """Test that API endpoints are properly structured."""
        from stream_sniper.api.asgi import app

        # Check the composed application surface via the OpenAPI schema:
        # router inclusion is lazy in FastAPI (routes flatten on demand), so
        # app.routes holds unresolved includes rather than APIRoute objects.
        actual_paths = [path for path in app.openapi()["paths"] if path.startswith("/admin/tracking")]

        # Check that we have the expected endpoints
        expected_paths = [
            "/streamers",
            "/streamers/{streamer_id}",
            "/jobs",
            "/stats",
            "/service/status",
            "/jobs/{job_id}/cancel",
            "/jobs/{job_id}/retry",
        ]

        for expected_path in expected_paths:
            assert any(expected_path in path for path in actual_paths), f"Missing endpoint: {expected_path}"

    def test_unsupported_cross_process_controls_are_not_advertised(self):
        from stream_sniper.api.asgi import app

        paths = app.openapi()["paths"]
        assert "/admin/tracking/service/start" not in paths
        assert "/admin/tracking/service/stop" not in paths
        assert "/admin/tracking/service/restart" not in paths

    def test_service_lifecycle(self):
        """Test service lifecycle management."""
        from stream_sniper.tracking.scheduler import TrackingScheduler

        scheduler = TrackingScheduler()

        # Test initial state
        assert scheduler.is_running() == False

        # Test uptime before start
        assert scheduler.get_uptime() is None

    def test_configuration_validation(self):
        """Test that configuration values are validated."""
        # Test invalid configuration values
        with pytest.raises(ValueError):
            ProcessingQueue(max_concurrent_jobs=0)

        with pytest.raises(ValueError):
            ProcessingQueue(max_retries=-1)

    def test_concurrent_job_limiting(self):
        """Test that concurrent job limiting works correctly."""
        queue = ProcessingQueue(max_concurrent_jobs=2)

        # Test that queue respects concurrent job limits
        status = queue.get_queue_status()
        assert status.max_concurrent_jobs == 2

    @pytest.mark.asyncio
    async def test_scheduler_surfaces_component_failure_and_resets_state(self, mock_twitch_api, monkeypatch):
        scheduler = TrackingScheduler(monitor_interval=60)
        scheduler.MAX_COMPONENT_RESTARTS = 0
        monkeypatch.setattr(scheduler.stream_monitor, "initialize", AsyncMock())
        monkeypatch.setattr(
            scheduler.stream_monitor,
            "start_monitoring",
            AsyncMock(side_effect=RuntimeError("monitor crashed")),
        )

        async def wait_forever():
            await asyncio.Event().wait()

        monkeypatch.setattr(scheduler.processing_queue, "run_until_stopped", wait_forever)
        monkeypatch.setattr(scheduler, "_heartbeat_loop", wait_forever)

        with pytest.raises(RuntimeError, match="monitor crashed"):
            await scheduler.start()

        assert scheduler.is_running() is False
        assert scheduler.get_status().scheduler.running is False

    @pytest.mark.asyncio
    async def test_scheduler_restarts_a_failed_component_once(self, mock_twitch_api, monkeypatch):
        scheduler = TrackingScheduler(monitor_interval=60)
        scheduler.MAX_COMPONENT_RESTARTS = 1
        scheduler.RESTART_BACKOFF_BASE_SECONDS = 0
        monkeypatch.setattr(scheduler.stream_monitor, "initialize", AsyncMock())
        starts = 0

        async def fail_then_stop():
            nonlocal starts
            starts += 1
            if starts == 1:
                raise RuntimeError("transient monitor crash")
            scheduler._running = False

        async def wait_forever():
            await asyncio.Event().wait()

        monkeypatch.setattr(scheduler.stream_monitor, "start_monitoring", fail_then_stop)
        monkeypatch.setattr(scheduler.processing_queue, "run_until_stopped", wait_forever)
        monkeypatch.setattr(scheduler, "_heartbeat_loop", wait_forever)

        await scheduler.start()

        assert starts == 2
        assert scheduler.is_running() is False
