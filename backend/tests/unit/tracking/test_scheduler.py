"""Lifecycle regression tests for the tracking scheduler."""

import asyncio
from unittest.mock import AsyncMock, Mock

import pytest
from psycopg2 import OperationalError

from stream_sniper.tracking.scheduler import TrackingScheduler


@pytest.mark.asyncio
async def test_shutdown_attempts_every_cleanup_and_aggregates_failures(monkeypatch):
    scheduler = object.__new__(TrackingScheduler)
    scheduler.logger = Mock()
    scheduler.stream_monitor = Mock()
    scheduler.stream_monitor.close = AsyncMock(side_effect=RuntimeError("monitor"))
    scheduler.processing_queue = Mock()
    scheduler.processing_queue.shutdown = AsyncMock(side_effect=RuntimeError("queue"))
    scheduler._tasks = []
    heartbeat_delete = Mock(side_effect=RuntimeError("heartbeat"))
    monkeypatch.setattr("stream_sniper.tracking.scheduler.delete_heartbeat", heartbeat_delete)

    with pytest.raises(ExceptionGroup) as raised:
        await scheduler._shutdown_components(clear_heartbeat=True)

    assert [str(error) for error in raised.value.exceptions] == ["monitor", "queue", "heartbeat"]
    scheduler.stream_monitor.close.assert_awaited_once_with()
    scheduler.processing_queue.shutdown.assert_awaited_once_with()
    heartbeat_delete.assert_called_once_with()


@pytest.mark.asyncio
async def test_shutdown_cancels_owned_tasks_without_reporting_cancellation(monkeypatch):
    scheduler = object.__new__(TrackingScheduler)
    scheduler.logger = Mock()
    scheduler.stream_monitor = Mock()
    scheduler.stream_monitor.close = AsyncMock()
    scheduler.processing_queue = Mock()
    scheduler.processing_queue.shutdown = AsyncMock()
    scheduler._tasks = [asyncio.create_task(asyncio.sleep(60))]
    monkeypatch.setattr("stream_sniper.tracking.scheduler.delete_heartbeat", Mock())

    await scheduler._shutdown_components(clear_heartbeat=True)

    assert scheduler._tasks == []


@pytest.mark.asyncio
async def test_heartbeat_retries_expected_database_failure(monkeypatch):
    scheduler = object.__new__(TrackingScheduler)
    scheduler.logger = Mock()
    scheduler._running = True
    scheduler.get_status = Mock()

    def fail_write(_status):
        scheduler._running = False
        raise OperationalError("database unavailable")

    monkeypatch.setattr("stream_sniper.tracking.scheduler.write_heartbeat", fail_write)
    monkeypatch.setattr("stream_sniper.tracking.scheduler.HEARTBEAT_INTERVAL", 0)

    await scheduler._heartbeat_loop()

    scheduler.logger.exception.assert_called_once_with("Heartbeat write failed")


@pytest.mark.asyncio
async def test_heartbeat_propagates_unexpected_failure(monkeypatch):
    scheduler = object.__new__(TrackingScheduler)
    scheduler.logger = Mock()
    scheduler._running = True
    scheduler.get_status = Mock(side_effect=RuntimeError("status bug"))

    with pytest.raises(RuntimeError, match="status bug"):
        await scheduler._heartbeat_loop()
