"""Behavior tests for the API server entry point."""

from types import SimpleNamespace
from unittest.mock import patch

from stream_sniper.api import server


def test_api_server_passes_runtime_config_to_uvicorn() -> None:
    config = SimpleNamespace(host="127.0.0.1", port=5002)
    with (
        patch.object(server, "setup_logging"),
        patch("stream_sniper.api.asgi.app") as app,
        patch.object(server.uvicorn, "run") as run,
    ):
        app.state.config = config
        assert server.run() == 0

    assert run.call_args.kwargs["host"] == "127.0.0.1"
    assert run.call_args.kwargs["port"] == 5002
