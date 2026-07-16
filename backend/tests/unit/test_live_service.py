"""Behavior tests for the live-service entry point."""

from unittest.mock import patch

from stream_sniper.collector.live import service as live_service


def test_live_entrypoint_returns_runtime_result() -> None:
    def finish(coroutine):
        coroutine.close()
        return 0

    with patch.object(live_service.asyncio, "run", side_effect=finish) as run:
        assert live_service.run_live_service() == 0
        run.assert_called_once()
