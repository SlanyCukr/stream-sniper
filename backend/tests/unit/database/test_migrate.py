"""Behavior tests for the packaged migration command."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from stream_sniper.database.commands import migrate


def test_migration_entrypoint_uses_packaged_script_location() -> None:
    command_line = MagicMock()
    command_line.parser.parse_args.return_value = SimpleNamespace(cmd=(lambda: None))
    with patch.object(migrate, "CommandLine", return_value=command_line):
        migrate.main(["heads"])

    config = command_line.run_cmd.call_args.args[0]
    assert config.get_main_option("script_location").endswith("stream_sniper/database/migrations")
