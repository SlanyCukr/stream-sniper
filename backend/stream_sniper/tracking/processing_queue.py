import asyncio
from dataclasses import dataclass
from typing import Literal
from uuid import uuid4

from ..database.gateways.tracking.processing_jobs_table_gateway import (
    ClaimedProcessingJob,
    cancel_processing_job_db,
    claim_processing_jobs_db,
    complete_processing_job_and_advance_streamer_db,
    fail_processing_job_db,
    processing_job_cancellation_requested_db,
)
from ..logging_config import get_logger
from .status import ProcessingQueueStatus
from .stream_processor import run_vod_job

logger = get_logger(__name__)
JobTerminalOutcome = Literal["completed", "failed", "cancelled"]


@dataclass(frozen=True)
class ActiveProcessingJob:
    claim: ClaimedProcessingJob
    task: asyncio.Task[JobTerminalOutcome]


class ProcessingQueue:
    def __init__(self, max_concurrent_jobs: int = 3, max_retries: int = 3):
        if max_concurrent_jobs < 1:
            raise ValueError("max_concurrent_jobs must be at least 1")
        if max_retries < 0:
            raise ValueError("max_retries must not be negative")
        self.max_concurrent_jobs = max_concurrent_jobs
        self.max_retries = max_retries
        self.logger = get_logger(__name__)
        self._running = False
        self._active_jobs: dict[int, ActiveProcessingJob] = {}

    async def run_until_stopped(self) -> None:
        self._running = True
        try:
            while self._running:
                await self._process_queue()
                await asyncio.sleep(10)
        finally:
            self._running = False

    async def shutdown(self) -> None:
        self._running = False
        for job_id, active in self._active_jobs.items():
            if not active.task.done() and active.task.cancelling() == 0:
                active.task.cancel()
                self.logger.info(f"Cancelled job {job_id}")

        active_jobs = list(self._active_jobs.items())
        results = await asyncio.gather(
            *(active.task for _, active in active_jobs),
            return_exceptions=True,
        )
        self._active_jobs.clear()
        failures: list[Exception] = []
        for (job_id, _), result in zip(active_jobs, results, strict=True):
            if isinstance(result, asyncio.CancelledError):
                continue
            if isinstance(result, Exception):
                self.logger.error("Job %s failed during queue shutdown: %s", job_id, result)
                failures.append(result)
            elif isinstance(result, BaseException):
                raise result
        if failures:
            raise ExceptionGroup("Processing jobs failed during queue shutdown", failures)

    async def _process_queue(self) -> None:
        self._cleanup_completed_jobs()
        await self._cancel_requested_jobs()
        if len(self._active_jobs) >= self.max_concurrent_jobs:
            return

        available_slots = self.max_concurrent_jobs - len(self._active_jobs)
        claimed_jobs = await asyncio.to_thread(
            claim_processing_jobs_db,
            limit=available_slots,
            max_retries=self.max_retries,
            worker_token=uuid4().hex,
        )

        for claimed in claimed_jobs:
            job_id = claimed.job.id
            task = asyncio.create_task(self._process_job(claimed))
            self._active_jobs[job_id] = ActiveProcessingJob(claimed, task)
            self.logger.info(f"Started processing job {job_id}")

    def _cleanup_completed_jobs(self) -> None:
        for job_id, active in list(self._active_jobs.items()):
            if not active.task.done():
                continue
            try:
                outcome = active.task.result()
            except asyncio.CancelledError:
                self.logger.error("Job %s task was cancelled without a terminal outcome", job_id)
            except Exception:
                self.logger.exception("Job %s task failed before a terminal transition", job_id)
            else:
                self.logger.info("Job %s reached terminal outcome %s", job_id, outcome)
            del self._active_jobs[job_id]

    async def _cancel_requested_jobs(self) -> None:
        """Cancel local tasks whose matching leases were durably requested."""
        for job_id, active in list(self._active_jobs.items()):
            requested = await asyncio.to_thread(
                processing_job_cancellation_requested_db,
                job_id,
                active.claim.worker_token,
            )
            if requested and not active.task.done() and active.task.cancelling() == 0:
                active.task.cancel()
                self.logger.info("Honouring durable cancellation for job %s", job_id)

    async def _process_job(self, claimed: ClaimedProcessingJob) -> JobTerminalOutcome:
        job = claimed.job
        job_id = job.id
        twitch_vod_id = job.twitch_vod_id
        twitch_username = job.twitch_username

        try:
            self.logger.info(f"Processing job {job_id} for Twitch VOD {twitch_vod_id} by {twitch_username}")
            result = await run_vod_job(twitch_username, twitch_vod_id)
            if result.twitch_vod_id != twitch_vod_id:
                raise RuntimeError(f"Job requested Twitch VOD {twitch_vod_id}, got {result.twitch_vod_id}")
            if await asyncio.to_thread(processing_job_cancellation_requested_db, job_id, claimed.worker_token):
                raise asyncio.CancelledError
            if not await asyncio.to_thread(
                complete_processing_job_and_advance_streamer_db,
                job_id,
                claimed.worker_token,
            ):
                raise RuntimeError(f"Lost lease while completing job {job_id}")
            self.logger.info(f"Job {job_id} completed successfully")
            return "completed"

        except asyncio.CancelledError:
            self.logger.info(f"Job {job_id} was cancelled")
            transitioned = await asyncio.to_thread(
                cancel_processing_job_db,
                job_id,
                worker_token=claimed.worker_token,
                terminal_retry_count=self.max_retries,
            )
            if not transitioned:
                raise RuntimeError(f"Lost lease while cancelling job {job_id}") from None
            return "cancelled"
        except Exception as e:
            self.logger.exception("Error processing job %s", job_id)
            transitioned = await asyncio.to_thread(
                fail_processing_job_db, job_id, str(e), worker_token=claimed.worker_token
            )
            if not transitioned:
                raise RuntimeError(f"Lost lease while failing job {job_id}") from e
            return "failed"

    def get_queue_status(self) -> ProcessingQueueStatus:
        return ProcessingQueueStatus(
            running=self._running,
            active_jobs=len(self._active_jobs),
            max_concurrent_jobs=self.max_concurrent_jobs,
            max_retries=self.max_retries,
            active_job_ids=list(self._active_jobs),
        )
