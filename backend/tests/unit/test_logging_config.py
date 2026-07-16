"""Regression tests for explicit, repeatable process logging setup."""

import logging

import pytest

from stream_sniper import logging_config


def _owned_handlers() -> list[logging.Handler]:
    return [handler for handler in logging.getLogger().handlers if getattr(handler, "_stream_sniper_owned", False)]


def test_get_logger_has_no_configuration_side_effect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(logging_config, "_logging_config", None)
    before = list(logging.getLogger().handlers)

    logger = logging_config.get_logger("stream_sniper.test")

    assert logger.name == "stream_sniper.test"
    assert logging_config.is_logging_configured() is False
    assert logging.getLogger().handlers == before


def test_repeated_setup_replaces_owned_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(logging_config, "_logging_config", None)
    logging_config.setup_logging(enable_file_logging=False, enable_console_logging=True)
    first = _owned_handlers()

    logging_config.setup_logging(enable_file_logging=False, enable_console_logging=True)
    second = _owned_handlers()

    assert len(first) == len(second) == 1
    assert second[0] is not first[0]


def test_later_setup_options_take_effect(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(logging_config, "_logging_config", None)
    logging_config.setup_logging(enable_file_logging=False, enable_console_logging=True, log_level="INFO")

    root = logging_config.setup_logging(
        enable_file_logging=False,
        enable_console_logging=False,
        log_level="DEBUG",
    )

    assert root.level == logging.DEBUG
    assert _owned_handlers() == []
