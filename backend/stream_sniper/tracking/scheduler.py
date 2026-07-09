"""
Scheduler service for coordinating stream monitoring and processing.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, Optional

from ..logging_config import get_logger
from .heartbeat import HEARTBEAT_INTERVAL, delete_heartbeat, write_heartbeat
from .processing_queue import ProcessingQueue
from .stream_monitor import StreamMonitor

logger = get_logger(__name__)


class TrackingScheduler:
    """
    Main scheduler service that coordinates stream monitoring and processing.
    """
    
    def __init__(
        self,
        monitor_interval: int = 300,  # 5 minutes
        max_concurrent_jobs: int = 3,
        max_retries: int = 3
    ):
        self.monitor_interval = monitor_interval
        self.max_concurrent_jobs = max_concurrent_jobs
        self.max_retries = max_retries
        self.logger = get_logger(__name__)
        self._running = False
        self._start_time: Optional[datetime] = None
        self._tasks: list[asyncio.Task] = []

        # Initialize components
        self.stream_monitor = StreamMonitor(check_interval=monitor_interval)
        self.processing_queue = ProcessingQueue(
            max_concurrent_jobs=max_concurrent_jobs,
            max_retries=max_retries
        )
        
    async def start(self):
        """Start the tracking scheduler."""
        if self._running:
            self.logger.warning("Scheduler is already running")
            return
            
        self._running = True
        self._start_time = datetime.now()
        self.logger.info("Starting tracking scheduler...")
        
        try:
            # Initialize stream monitor
            await self.stream_monitor.initialize()
            
            # Start both services concurrently, plus a heartbeat that publishes
            # this process's status to Postgres so the (separate) API process can
            # report real monitoring health on the admin dashboard.
            self._tasks = [
                asyncio.create_task(self.stream_monitor.start_monitoring()),
                asyncio.create_task(self.processing_queue.start_processing()),
                asyncio.create_task(self._heartbeat_loop())
            ]

            self.logger.info("Tracking scheduler started successfully")

            # Wait for both tasks to complete (they run indefinitely)
            await asyncio.gather(*self._tasks, return_exceptions=True)
            
        except Exception as e:
            self.logger.error(f"Error in tracking scheduler: {e}")
            raise
        finally:
            self.logger.info("Tracking scheduler stopped")
            
    async def stop(self):
        """Stop the tracking scheduler."""
        if not self._running:
            self.logger.warning("Scheduler is not running")
            return
            
        self._running = False
        self.logger.info("Stopping tracking scheduler...")
        
        # Stop both services
        await asyncio.gather(
            self.stream_monitor.stop_monitoring(),
            self.processing_queue.stop_processing(),
            return_exceptions=True
        )

        # The service loops may be parked in long sleeps (up to the monitor
        # interval) and only re-check their running flag afterwards — cancel
        # them so shutdown is immediate.
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []

        # Clear the published heartbeat so the dashboard reflects 'down' at once
        # instead of waiting for the key's TTL to lapse.
        await asyncio.to_thread(delete_heartbeat)

        self.logger.info("Tracking scheduler stopped successfully")

    async def _heartbeat_loop(self):
        """Publish this process's status to Postgres on a fixed interval.

        Runs the blocking DB write in a worker thread so a slow/timed-out
        query can't stall the monitor or processing-queue coroutines.
        """
        while self._running:
            try:
                await asyncio.to_thread(write_heartbeat, self.get_status())
            except Exception as e:
                self.logger.warning(f"Heartbeat write failed: {e}")
            await asyncio.sleep(HEARTBEAT_INTERVAL)
    
    async def restart(self):
        """Restart the tracking scheduler."""
        self.logger.info("Restarting tracking scheduler...")
        await self.stop()
        await asyncio.sleep(2)  # Brief pause
        await self.start()
    
    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the tracking system."""
        uptime_seconds = None
        if self._start_time:
            uptime_seconds = (datetime.now() - self._start_time).total_seconds()
        
        return {
            'scheduler': {
                'running': self._running,
                'start_time': self._start_time.isoformat() if self._start_time else None,
                'uptime_seconds': uptime_seconds,
                'monitor_interval': self.monitor_interval,
                'max_concurrent_jobs': self.max_concurrent_jobs,
                'max_retries': self.max_retries
            },
            'stream_monitor': self.stream_monitor.get_monitoring_stats(),
            'processing_queue': self.processing_queue.get_queue_status()
        }
    
    async def check_streamer_now(self, twitch_username: str):
        """Manually check a specific streamer's status."""
        return await self.stream_monitor.check_streamer_now(twitch_username)
    
    async def cancel_job(self, job_id: int) -> bool:
        """Cancel a specific processing job."""
        return await self.processing_queue.cancel_job(job_id)
    
    async def retry_job(self, job_id: int) -> bool:
        """Retry a specific processing job."""
        return await self.processing_queue.retry_job(job_id)
    
    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self._running
    
    def get_uptime(self) -> Optional[float]:
        """Get scheduler uptime in seconds."""
        if not self._start_time:
            return None
        return (datetime.now() - self._start_time).total_seconds()


# Global scheduler instance
_scheduler: Optional[TrackingScheduler] = None


def get_scheduler() -> TrackingScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = TrackingScheduler()
    return _scheduler


async def start_tracking_system():
    """Start the global tracking system."""
    scheduler = get_scheduler()
    await scheduler.start()


async def stop_tracking_system():
    """Stop the global tracking system."""
    scheduler = get_scheduler()
    await scheduler.stop()


def get_tracking_system_status() -> Dict[str, Any]:
    """Get the status of the global tracking system."""
    scheduler = get_scheduler()
    return scheduler.get_status()