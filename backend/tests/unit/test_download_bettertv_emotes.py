"""Contract tests for the canonical BTTV dataset generator command."""

import importlib.util
from pathlib import Path
from types import ModuleType


def _load_generator() -> ModuleType:
    script = Path(__file__).parents[3] / "tools/refresh_bettertv_emotes.py"
    spec = importlib.util.spec_from_file_location("download_bettertv_emotes", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_checked_bttv_consumers_match_semantically() -> None:
    generator = _load_generator()

    assert generator.check() == 0


def test_atomic_dataset_writer_sorts_and_round_trips(tmp_path) -> None:
    generator = _load_generator()
    target = tmp_path / "nested/emotes.json"

    generator._atomic_write_dataset(target, {"z": "2", "a": "1"})

    assert generator._read_dataset(target) == {"a": "1", "z": "2"}
    assert target.read_text().index('"a"') < target.read_text().index('"z"')
