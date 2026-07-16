"""Behavior tests for the live authentication command."""

import os
from pathlib import Path

from stream_sniper.collector.live import auth_cli as live_auth_cli


def test_live_auth_token_file_is_private(tmp_path: Path) -> None:
    token_file = tmp_path / "tokens/live-refresh-token"

    assert live_auth_cli._save_token(token_file, "secret-token") == token_file.resolve()
    assert token_file.read_text() == "secret-token"
    assert os.stat(token_file).st_mode & 0o777 == 0o600
