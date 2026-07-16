"""Atomic leased processing queue tests."""

import asyncio
import threading
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from stream_sniper.application.tracking.models import ProcessingJob
from stream_sniper.database.gateways.tracking.processing_jobs_table_gateway import ClaimedProcessingJob
from stream_sniper.tracking import processing_queue as queue_module
from stream_sniper.tracking import stream_processor
from stream_sniper.tracking.processing_queue import ActiveProcessingJob, ProcessingQueue


def _claim(job_id: int = 7) -> ClaimedProcessingJob:
    now = datetime(2026, 7, 15, 12)
    return ClaimedProcessingJob(
        ProcessingJob(
            job_id,
            1,
            999,
            "in_progress",
            now,
            None,
            None,
            0,
            now,
            now,
            "streamer",
            "Streamer",
            None,
            None,
        ),
        "lease-token",
    )


@pytest.mark.asyncio
async def test_completed_tasks_are_removed_before_capacity_check(monkeypatch):
    queue = ProcessingQueue(max_concurrent_jobs=1)
    completed = asyncio.create_task(asyncio.sleep(0))
    await completed
    queue._active_jobs[1] = ActiveProcessingJob(_claim(), completed)  # type: ignore[arg-type]
    claim = Mock(return_value=[])
    monkeypatch.setattr(queue_module, "claim_processing_jobs_db", claim)

    await queue._process_queue()

    assert queue._active_jobs == {}
    assert claim.call_args.kwargs["limit"] == 1


@pytest.mark.asyncio
async def test_job_can_only_complete_the_exact_requested_vod(monkeypatch):
    queue = ProcessingQueue(max_concurrent_jobs=1)
    monkeypatch.setattr(
        queue_module,
        "run_vod_job",
        AsyncMock(return_value=SimpleNamespace(twitch_vod_id=1000)),
    )
    completed = Mock(return_value=True)
    failed = Mock(return_value=True)
    monkeypatch.setattr(queue_module, "complete_processing_job_and_advance_streamer_db", completed)
    monkeypatch.setattr(queue_module, "fail_processing_job_db", failed)

    await queue._process_job(_claim())

    completed.assert_not_called()
    failed.assert_called_once()
    assert failed.call_args.kwargs["worker_token"] == "lease-token"


@pytest.mark.asyncio
async def test_blocked_claim_does_not_stall_event_loop(monkeypatch):
    queue = ProcessingQueue(max_concurrent_jobs=1)
    release = threading.Event()

    def blocked_claim(**_kwargs):
        release.wait(timeout=2)
        return []

    monkeypatch.setattr(queue_module, "claim_processing_jobs_db", blocked_claim)
    task = asyncio.create_task(queue._process_queue())

    await asyncio.sleep(0.02)

    assert task.done() is False
    release.set()
    await task


@pytest.mark.asyncio
async def test_durable_cancellation_cancels_matching_local_lease(monkeypatch):
    queue = ProcessingQueue(max_concurrent_jobs=1)

    async def running_job():
        await asyncio.Event().wait()
        return "completed"

    task = asyncio.create_task(running_job())
    queue._active_jobs[7] = ActiveProcessingJob(_claim(), task)  # type: ignore[arg-type]
    monkeypatch.setattr(queue_module, "processing_job_cancellation_requested_db", Mock(return_value=True))

    await queue._cancel_requested_jobs()
    await asyncio.gather(task, return_exceptions=True)

    assert task.cancelled() is True


@pytest.mark.asyncio
async def test_threaded_vod_cancellation_waits_for_worker_shutdown(monkeypatch):
    worker_started = threading.Event()
    release_worker = threading.Event()
    ingestion = SimpleNamespace(twitch_vod_id=999)

    class BlockingCollector:
        def __init__(self, *_args, **_kwargs):
            pass

        def ingest_archived_vods(self, *, max_vods):
            assert max_vods == 1
            worker_started.set()
            release_worker.wait(timeout=2)
            return SimpleNamespace(processed_count=1, processed_vods=(ingestion,))

    monkeypatch.setattr(stream_processor, "TwitchCollectorFacade", BlockingCollector)
    task = asyncio.create_task(stream_processor.run_vod_job("streamer", 999))
    await asyncio.to_thread(worker_started.wait, 2)

    task.cancel()
    await asyncio.sleep(0.02)
    assert task.done() is False

    task.cancel()
    await asyncio.sleep(0.02)
    assert task.done() is False

    release_worker.set()
    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_threaded_vod_cancellation_wins_over_late_worker_failure(monkeypatch):
    worker_started = threading.Event()
    release_worker = threading.Event()

    class FailingCollector:
        def __init__(self, *_args, **_kwargs):
            pass

        def ingest_archived_vods(self, *, max_vods):
            assert max_vods == 1
            worker_started.set()
            release_worker.wait(timeout=2)
            raise RuntimeError("late ingestion failure")

    monkeypatch.setattr(stream_processor, "TwitchCollectorFacade", FailingCollector)
    task = asyncio.create_task(stream_processor.run_vod_job("streamer", 999))
    await asyncio.to_thread(worker_started.wait, 2)

    task.cancel()
    release_worker.set()

    with pytest.raises(asyncio.CancelledError):
        await task


@pytest.mark.asyncio
async def test_cancelled_job_becomes_non_retryable_only_after_worker_stops(monkeypatch):
    queue = ProcessingQueue(max_concurrent_jobs=1, max_retries=3)
    monkeypatch.setattr(queue_module, "run_vod_job", AsyncMock(side_effect=asyncio.CancelledError))
    cancelled = Mock(return_value=True)
    monkeypatch.setattr(queue_module, "cancel_processing_job_db", cancelled)

    outcome = await queue._process_job(_claim())

    assert outcome == "cancelled"
    cancelled.assert_called_once_with(7, worker_token="lease-token", terminal_retry_count=3)


@pytest.mark.asyncio
async def test_failed_terminal_write_surfaces_from_worker_task(monkeypatch):
    queue = ProcessingQueue(max_concurrent_jobs=1)
    monkeypatch.setattr(
        queue_module,
        "run_vod_job",
        AsyncMock(side_effect=RuntimeError("collector failed")),
    )
    monkeypatch.setattr(queue_module, "fail_processing_job_db", Mock(return_value=False))

    with pytest.raises(RuntimeError, match="Lost lease while failing job 7"):
        await queue._process_job(_claim())


@pytest.mark.asyncio
async def test_capacity_bounded_claim_schedules_every_returned_job(monkeypatch):
    queue = ProcessingQueue(max_concurrent_jobs=3)
    blocked = asyncio.Event()

    async def wait_for_release(_claimed):
        await blocked.wait()
        return "completed"

    existing_task = asyncio.create_task(wait_for_release(_claim()))
    queue._active_jobs[7] = ActiveProcessingJob(_claim(), existing_task)  # type: ignore[arg-type]
    claim = Mock(return_value=[_claim(8), _claim(9)])
    monkeypatch.setattr(queue_module, "processing_job_cancellation_requested_db", Mock(return_value=False))
    monkeypatch.setattr(queue_module, "claim_processing_jobs_db", claim)
    monkeypatch.setattr(queue, "_process_job", wait_for_release)

    await queue._process_queue()

    assert claim.call_args.kwargs["limit"] == 2
    assert set(queue._active_jobs) == {7, 8, 9}
    assert all(not active.task.done() for active in queue._active_jobs.values())

    for active in queue._active_jobs.values():
        active.task.cancel()
    await asyncio.gather(*(active.task for active in queue._active_jobs.values()), return_exceptions=True)


@pytest.mark.asyncio
async def test_failed_job_logs_traceback_before_terminal_transition(monkeypatch):
    queue = ProcessingQueue(max_concurrent_jobs=1)
    queue.logger = Mock()
    monkeypatch.setattr(queue_module, "run_vod_job", AsyncMock(side_effect=RuntimeError("collector failed")))
    failed = Mock(return_value=True)
    monkeypatch.setattr(queue_module, "fail_processing_job_db", failed)

    outcome = await queue._process_job(_claim())

    assert outcome == "failed"
    queue.logger.exception.assert_called_once_with("Error processing job %s", 7)
    failed.assert_called_once_with(7, "collector failed", worker_token="lease-token")


@pytest.mark.asyncio
async def test_shutdown_surfaces_worker_failures_after_clearing_active_jobs():
    queue = ProcessingQueue(max_concurrent_jobs=1)

    async def fail():
        raise RuntimeError("terminal transition failed")

    task = asyncio.create_task(fail())
    await asyncio.sleep(0)
    queue._active_jobs[7] = ActiveProcessingJob(_claim(), task)  # type: ignore[arg-type]

    with pytest.raises(ExceptionGroup, match="Processing jobs failed during queue shutdown") as caught:
        await queue.shutdown()

    assert [str(error) for error in caught.value.exceptions] == ["terminal transition failed"]
    assert queue._active_jobs == {}
