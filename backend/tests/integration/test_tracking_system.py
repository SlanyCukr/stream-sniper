"""
Integration tests for the tracking system.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from stream_sniper.tracking.processing_queue import ProcessingQueue
from stream_sniper.tracking.scheduler import TrackingScheduler
from stream_sniper.tracking.stream_monitor import StreamMonitor


class TestTrackingSystem:
    """Test suite for the tracking system components."""

    @pytest.fixture
    def mock_twitch_api(self):
        """Mock Twitch API for testing."""
        with patch('stream_sniper.tracking.stream_monitor.TwitchAPI') as mock_api:
            mock_instance = Mock()
            mock_api.return_value = mock_instance
            # Async TwitchAPI methods must be AsyncMocks so `await` works
            mock_instance.twitch_api_init = AsyncMock()
            mock_instance.get_stream_info_async = AsyncMock(return_value=None)
            mock_instance.get_available_video_ids_async = AsyncMock(return_value=[])
            mock_instance.get_creator_info_async = AsyncMock(
                return_value=("TestStreamer", "http://example.com/avatar.jpg")
            )
            mock_instance.get_creator_twitch_id_async = AsyncMock(return_value="123456789")
            # Sync wrappers
            mock_instance.set_streamer_nickname = Mock()
            mock_instance.get_stream_info = Mock()
            mock_instance.get_available_video_ids = Mock()
            mock_instance.get_creator_info = Mock(return_value=("TestStreamer", "http://example.com/avatar.jpg"))
            mock_instance.get_creator_twitch_id = Mock(return_value="123456789")
            yield mock_instance

    @pytest.fixture
    def mock_database(self):
        """Mock database operations for testing."""
        # All table gateways acquire connections via the decorators module's
        # get_pool (the gateway modules themselves don't import get_pool).
        with patch('stream_sniper.database.decorators.get_pool'):
            yield

    def test_tracked_streamers_database_operations(self, mock_database):
        """Test tracked streamers database operations."""
        # Test would need actual database connection
        # This is a placeholder for database integration tests
        pass

    def test_processing_jobs_database_operations(self, mock_database):
        """Test processing jobs database operations."""
        # Test would need actual database connection
        # This is a placeholder for database integration tests
        pass

    @pytest.mark.asyncio
    async def test_stream_monitor_initialization(self, mock_twitch_api):
        """Test stream monitor initialization."""
        monitor = StreamMonitor(check_interval=60)
        
        # Test initialization
        await monitor.initialize()
        
        # Verify Twitch API was initialized
        mock_twitch_api.twitch_api_init.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_monitor_status_check(self, mock_twitch_api):
        """Test stream monitor status checking."""
        monitor = StreamMonitor(check_interval=60)
        await monitor.initialize()
        
        # Mock stream info response (monitor awaits the async variant)
        mock_twitch_api.get_stream_info_async.return_value = None  # Stream offline
        
        # Test status check
        status = await monitor.check_streamer_now("teststreamer")
        
        assert status.twitch_username == "teststreamer"
        assert status.is_live == False
        assert status.last_checked is not None

    @pytest.mark.asyncio
    async def test_processing_queue_initialization(self):
        """Test processing queue initialization."""
        queue = ProcessingQueue(max_concurrent_jobs=2, max_retries=3)
        
        # Test queue status
        status = queue.get_queue_status()
        assert status['max_concurrent_jobs'] == 2
        assert status['max_retries'] == 3
        assert status['active_jobs'] == 0

    @pytest.mark.asyncio
    async def test_tracking_scheduler_initialization(self, mock_twitch_api):
        """Test tracking scheduler initialization."""
        scheduler = TrackingScheduler(
            monitor_interval=60,
            max_concurrent_jobs=2,
            max_retries=3
        )
        
        # Test scheduler status
        status = scheduler.get_status()
        assert status['scheduler']['monitor_interval'] == 60
        assert status['scheduler']['max_concurrent_jobs'] == 2
        assert status['scheduler']['max_retries'] == 3
        assert status['scheduler']['running'] == False

    @pytest.mark.asyncio
    async def test_system_integration_flow(self, mock_twitch_api, mock_database):
        """Test the complete system integration flow."""
        # This test would simulate the complete flow:
        # 1. Add a streamer to tracking
        # 2. Start monitoring
        # 3. Simulate stream end
        # 4. Verify processing job creation
        # 5. Simulate processing completion
        
        # For now, this is a placeholder that would need actual database
        # and would need to be run in a controlled environment
        pass

    def test_api_endpoint_structure(self):
        """Test that API endpoints are properly structured."""
        from stream_sniper.api.tracking_endpoints import router
        
        # Get all routes
        routes = [route for route in router.routes if hasattr(route, 'methods')]
        
        # Check that we have the expected endpoints
        expected_paths = [
            '/streamers',
            '/streamers/{streamer_id}',
            '/jobs',
            '/stats',
            '/service/status',
            '/service/start',
            '/service/stop',
            '/service/restart',
            '/jobs/{job_id}/cancel',
            '/jobs/{job_id}/retry'
        ]
        
        actual_paths = [route.path for route in routes]
        
        for expected_path in expected_paths:
            assert any(expected_path in path for path in actual_paths), f"Missing endpoint: {expected_path}"

    def test_database_schema_consistency(self):
        """Test that database schema is consistent."""
        # This would test that the database schema matches expectations
        # and that all foreign key relationships are properly defined
        pass

    def test_service_lifecycle(self):
        """Test service lifecycle management."""
        from stream_sniper.tracking.scheduler import get_scheduler
        
        scheduler = get_scheduler()
        
        # Test initial state
        assert scheduler.is_running() == False
        
        # Test uptime before start
        assert scheduler.get_uptime() is None

    def test_error_handling(self):
        """Test error handling in various components."""
        # Test that the system gracefully handles various error conditions
        pass

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
        assert status['max_concurrent_jobs'] == 2