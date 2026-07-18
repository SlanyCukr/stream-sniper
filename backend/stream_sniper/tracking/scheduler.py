import asyncio
import os
from datetime import datetime

from psycopg2 import Error as DatabaseError

from ..logging_config import get_logger
from .heartbeat import HEARTBEAT_INTERVAL, delete_heartbeat, write_heartbeat
from .processing_queue import ProcessingQueue
from .status import SchedulerStatus, TrackingStatus
from .stream_monitor import StreamMonitor, StreamStatus

logger = get_logger(__name__)


class TrackingScheduler:
    MAX_COMPONENT_RESTARTS = 3
    RESTART_BACKOFF_BASE_SECONDS = 1.0

    def __init__(
        self,
        monitor_interval: int = 300,  # 5 minutes
        max_concurrent_jobs: int = 3,
        max_retries: int = 3,
    ):
        self.monitor_interval = monitor_interval
        self.max_concurrent_jobs = max_concurrent_jobs
        self.max_retries = max_retries
        self.logger = get_logger(__name__)
        self._running = False
        self._start_time: datetime | None = None
        self._tasks: list[asyncio.Task] = []

        # Optional "went live" Discord alerts: the webhook is read once here, at the
        # single tracking config seam, and passed down to the monitor.
        self.stream_monitor = StreamMonitor(
            check_interval=monitor_interval,
            discord_webhook_url=os.getenv("TRACKING_DISCORD_WEBHOOK_URL"),
        )
        self.processing_queue = ProcessingQueue(max_concurrent_jobs=max_concurrent_jobs, max_retries=max_retries)

    async def start(self) -> None:
        if self._running:
            self.logger.warning("Scheduler is already running")
            return

        self._running = True
        self._start_time = datetime.now()
        try:
            await self.stream_monitor.initialize()
            restart_count = 0

            while self._running:
                self._tasks = [
                    asyncio.create_task(self.stream_monitor.start_monitoring()),
                    asyncio.create_task(self.processing_queue.run_until_stopped()),
                    asyncio.create_task(self._heartbeat_loop()),
                ]
                done, pending = await asyncio.wait(
                    self._tasks,
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if not self._running:
                    break

                failure: BaseException = RuntimeError("Tracking component stopped unexpectedly")
                for task in done:
                    if not task.cancelled() and (task_error := task.exception()) is not None:
                        failure = task_error
                        break
                for task in pending:
                    task.cancel()
                await asyncio.gather(*pending, return_exceptions=True)
                # Every task in this component generation has now been observed.
                # Do not feed the already-surfaced failure back into final cleanup.
                self._tasks = []

                restart_count += 1
                if restart_count > self.MAX_COMPONENT_RESTARTS:
                    raise failure

                delay = min(
                    self.RESTART_BACKOFF_BASE_SECONDS * (2 ** (restart_count - 1)),
                    30.0,
                )
                self.logger.error(
                    "Tracking component failed; restarting %s/%s in %.1fs: %s",
                    restart_count,
                    self.MAX_COMPONENT_RESTARTS,
                    delay,
                    failure,
                )
                await asyncio.sleep(delay)

        except Exception:
            self.logger.exception("Tracking scheduler failed")
            raise
        finally:
            self._running = False
            await self._shutdown_components(clear_heartbeat=True)
            self.logger.info("Tracking scheduler stopped")

    async def stop(self) -> None:
        if not self._running:
            self.logger.warning("Scheduler is not running")
            return

        self._running = False
        await self._shutdown_components(clear_heartbeat=True)

    async def _shutdown_components(self, *, clear_heartbeat: bool) -> None:
        """Attempt every owned cleanup and surface all non-cancellation failures."""
        failures: list[Exception] = []
        try:
            await self.stream_monitor.close()
        except Exception as error:
            failures.append(error)
        try:
            await self.processing_queue.shutdown()
        except Exception as error:
            failures.append(error)

        for task in self._tasks:
            task.cancel()
        task_results = await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        failures.extend(
            result
            for result in task_results
            if isinstance(result, Exception) and not isinstance(result, asyncio.CancelledError)
        )

        if clear_heartbeat:
            try:
                await asyncio.to_thread(delete_heartbeat)
            except Exception as error:
                failures.append(error)

        for failure in failures:
            self.logger.error("Tracking scheduler cleanup failed: %s", failure, exc_info=failure)
        if failures:
            raise ExceptionGroup("Tracking scheduler shutdown failed", failures)

    async def _heartbeat_loop(self) -> None:
        """Publish this process's status to Postgres on a fixed interval.

        Runs the blocking DB write in a worker thread so a slow/timed-out
        query can't stall the monitor or processing-queue coroutines.
        """
        while self._running:
            try:
                await asyncio.to_thread(write_heartbeat, self.get_status())
            except DatabaseError:
                self.logger.exception("Heartbeat write failed")
            await asyncio.sleep(HEARTBEAT_INTERVAL)

    async def restart(self) -> None:
        await self.stop()
        await asyncio.sleep(2)
        await self.start()

    def get_status(self) -> TrackingStatus:
        uptime_seconds = None
        if self._start_time:
            uptime_seconds = (datetime.now() - self._start_time).total_seconds()

        return TrackingStatus(
            scheduler=SchedulerStatus(
                running=self._running,
                start_time=self._start_time.isoformat() if self._start_time else None,
                uptime_seconds=uptime_seconds,
                monitor_interval=self.monitor_interval,
                max_concurrent_jobs=self.max_concurrent_jobs,
                max_retries=self.max_retries,
            ),
            stream_monitor=self.stream_monitor.get_monitoring_stats(),
            processing_queue=self.processing_queue.get_queue_status(),
        )

    async def check_streamer_now(self, twitch_username: str) -> StreamStatus:
        return await self.stream_monitor.check_streamer_now(twitch_username)

    def is_running(self) -> bool:
        return self._running

    def get_uptime(self) -> float | None:
        if not self._start_time:
            return None
        return (datetime.now() - self._start_time).total_seconds()
