import os

import pytest

from stream_sniper.collector.live.secure_files import write_private_text


def test_private_text_write_is_atomic_and_owner_only(tmp_path) -> None:
    target = tmp_path / "tokens/refresh-token"

    assert write_private_text(target, "first") == target.resolve()
    assert write_private_text(target, "replacement") == target.resolve()

    assert target.read_text() == "replacement"
    assert os.stat(target).st_mode & 0o777 == 0o600
    assert list(target.parent.iterdir()) == [target]


def test_failed_replace_removes_temporary_file(tmp_path, monkeypatch) -> None:
    target = tmp_path / "refresh-token"

    def fail_replace(self, destination):
        raise OSError("disk unavailable")

    monkeypatch.setattr("stream_sniper.collector.live.secure_files.Path.replace", fail_replace)

    with pytest.raises(OSError, match="disk unavailable"):
        write_private_text(target, "secret")

    assert list(tmp_path.iterdir()) == []
