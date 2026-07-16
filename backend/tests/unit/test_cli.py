"""Behavior tests for the collector console entry point."""

from unittest.mock import patch

from stream_sniper import cli


def test_collector_cli_help_returns_failure_without_username(capsys) -> None:
    with patch("sys.argv", ["stream-sniper"]):
        assert cli.main() == 1

    assert "Usage: stream-sniper" in capsys.readouterr().out
