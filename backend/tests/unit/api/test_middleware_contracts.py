"""Constructor contracts for request middleware configuration."""

from starlette.applications import Starlette

from stream_sniper.api.middleware import RequestLoggingMiddleware


def test_explicit_empty_skip_paths_logs_every_route() -> None:
    middleware = RequestLoggingMiddleware(Starlette(), skip_paths=[])

    assert middleware.skip_paths == []
