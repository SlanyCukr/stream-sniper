"""Lifecycle and signal behavior for the tracking-service entry point."""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from stream_sniper.tracking import service as tracking_service


def test_tracking_entrypoint_returns_runtime_result() -> None:
    def finish(coroutine):
        coroutine.close()
        return 0

    with patch.object(tracking_service.asyncio, "run", side_effect=finish):
        assert tracking_service.run_tracking_service() == 0


@pytest.mark.asyncio
async def test_main_constructs_registers_and_starts_scheduler() -> None:
    scheduler = Mock()
    scheduler.start = AsyncMock()
    logger = Mock()

    with (
        patch.object(tracking_service, "setup_logging") as setup_logging,
        patch.object(tracking_service, "get_logger", return_value=logger),
        patch.object(tracking_service, "setup_signal_handlers") as setup_handlers,
        patch("stream_sniper.tracking.scheduler.TrackingScheduler", return_value=scheduler),
    ):
        result = await tracking_service.main.__wrapped__()

    assert result == 0
    setup_logging.assert_called_once_with(environment="production")
    setup_handlers.assert_called_once_with(scheduler, logger)
    scheduler.start.assert_awaited_once_with()
    logger.info.assert_any_call("Tracking service stopped")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("failure", "exit_code", "message"),
    [
        (KeyboardInterrupt(), 0, "Received keyboard interrupt, shutting down..."),
        (RuntimeError("scheduler failed"), 1, "Fatal error in tracking service: scheduler failed"),
    ],
)
async def test_main_maps_scheduler_failures_to_exit_codes(failure, exit_code, message) -> None:
    scheduler = Mock()
    scheduler.start = AsyncMock(side_effect=failure)
    logger = Mock()

    with (
        patch.object(tracking_service, "get_logger", return_value=logger),
        patch.object(tracking_service, "setup_signal_handlers"),
        patch("stream_sniper.tracking.scheduler.TrackingScheduler", return_value=scheduler),
    ):
        result = await tracking_service.main.__wrapped__()

    assert result == exit_code
    if exit_code == 0:
        logger.info.assert_any_call(message)
    else:
        logger.error.assert_called_once_with(message, exc_info=True)
    logger.info.assert_called_with("Tracking service stopped")


def test_signal_handlers_register_both_signals_and_schedule_stop() -> None:
    loop = Mock()
    scheduled = []

    def create_task(coroutine):
        scheduled.append(coroutine)
        coroutine.close()

    loop.create_task.side_effect = create_task
    scheduler = Mock()
    scheduler.stop = AsyncMock()
    logger = Mock()

    with patch.object(tracking_service.asyncio, "get_running_loop", return_value=loop):
        tracking_service.setup_signal_handlers(scheduler, logger)

    assert [call.args[0] for call in loop.add_signal_handler.call_args_list] == [
        tracking_service.signal.SIGINT,
        tracking_service.signal.SIGTERM,
    ]
    callback, signum = loop.add_signal_handler.call_args_list[0].args[1:]
    callback(signum)
    assert len(scheduled) == 1
    logger.info.assert_called_once_with(f"Received signal {signum}, shutting down gracefully...")


def test_signal_handlers_use_platform_fallback_when_loop_registration_is_unavailable() -> None:
    loop = Mock()
    loop.add_signal_handler.side_effect = NotImplementedError
    handlers = {}
    scheduler = Mock()
    scheduler.stop = AsyncMock()

    with (
        patch.object(tracking_service.asyncio, "get_running_loop", return_value=loop),
        patch.object(
            tracking_service.signal, "signal", side_effect=lambda sig, handler: handlers.setdefault(sig, handler)
        ),
    ):
        tracking_service.setup_signal_handlers(scheduler, Mock())

    assert set(handlers) == {tracking_service.signal.SIGINT, tracking_service.signal.SIGTERM}


@pytest.mark.parametrize(("failure", "expected"), [(KeyboardInterrupt(), 0), (RuntimeError("boom"), 1)])
def test_tracking_entrypoint_maps_outer_failures(failure, expected) -> None:
    with patch.object(tracking_service.asyncio, "run", side_effect=failure):
        assert tracking_service.run_tracking_service() == expected
