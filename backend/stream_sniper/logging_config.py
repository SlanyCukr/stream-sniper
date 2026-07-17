"""
Centralized logging configuration for Stream Sniper.

This module provides structured logging with JSON formatters, correlation IDs,
log rotation, and environment-based configuration.
"""

import contextvars
import json
import logging
import logging.handlers
import sys
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from types import TracebackType
from typing import TypedDict, Unpack

correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")
DEFAULT_MAX_LOG_FILE_SIZE_BYTES = 10 * 1_024 * 1_024


class LoggingOptions(TypedDict, total=False):
    """Supported keyword options for :func:`setup_logging`."""

    log_level: str | int
    log_dir: str | Path | None
    enable_file_logging: bool
    enable_console_logging: bool
    enable_json_logging: bool | None
    max_file_size: int
    backup_count: int
    correlation_id_enabled: bool


class CorrelationIDFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get("")
        return True


class JSONFormatter(logging.Formatter):
    def __init__(self, include_extra_fields: bool = True):
        super().__init__()
        self.include_extra_fields = include_extra_fields

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        correlation_id = getattr(record, "correlation_id", "")
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if self.include_extra_fields:
            for key, value in record.__dict__.items():
                if key not in {
                    "name",
                    "msg",
                    "args",
                    "levelname",
                    "levelno",
                    "pathname",
                    "filename",
                    "module",
                    "lineno",
                    "funcName",
                    "created",
                    "msecs",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "processName",
                    "process",
                    "message",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "correlation_id",
                }:
                    log_data[key] = value

        return json.dumps(log_data, default=str, ensure_ascii=False)


class ColoredConsoleFormatter(logging.Formatter):
    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, use_colors: bool = True):
        super().__init__()
        self.use_colors = use_colors and hasattr(sys.stderr, "isatty") and sys.stderr.isatty()

    def format(self, record: logging.LogRecord) -> str:
        correlation_id = getattr(record, "correlation_id", "")
        correlation_part = f" [{correlation_id[:8]}]" if correlation_id else ""

        if self.use_colors:
            color = self.COLORS.get(record.levelname, "")
            reset = self.RESET
            level_colored = f"{color}{record.levelname:<8}{reset}"
        else:
            level_colored = f"{record.levelname:<8}"

        timestamp = self.formatTime(record, "%Y-%m-%d %H:%M:%S")

        log_line = (
            f"{timestamp} | {level_colored} | "
            f"{record.name:<20} | {record.funcName}:{record.lineno:<4}{correlation_part} | "
            f"{record.getMessage()}"
        )

        if record.exc_info:
            log_line += f"\n{self.formatException(record.exc_info)}"

        return log_line


class PerformanceTimer:
    """Context manager for measuring performance."""

    def __init__(self, logger: logging.Logger, operation: str, level: int = logging.INFO, slow_threshold: float = 1.0):
        self.logger = logger
        self.operation = operation
        self.level = level
        self.slow_threshold = slow_threshold
        self.start_time = 0.0

    def __enter__(self) -> PerformanceTimer:
        self.start_time = time.time()
        self.logger.log(self.level, f"Starting {self.operation}")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        duration = time.time() - self.start_time

        if duration >= self.slow_threshold:
            level = logging.WARNING
            status = "SLOW"
        else:
            level = self.level
            status = "COMPLETED"

        self.logger.log(
            level,
            f"{status}: {self.operation}",
            extra={
                "duration_seconds": round(duration, 3),
                "performance_status": status.lower(),
                "slow_threshold": self.slow_threshold,
            },
        )


@contextmanager
def correlation_context(correlation_id: str | None = None) -> Iterator[str]:
    """Context manager for setting correlation ID."""
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())

    token = correlation_id_var.set(correlation_id)
    try:
        yield correlation_id
    finally:
        correlation_id_var.reset(token)


def get_correlation_id() -> str:
    return correlation_id_var.get("")


def set_correlation_id(correlation_id: str) -> None:
    correlation_id_var.set(correlation_id)


class LoggingConfig:
    """Centralized logging configuration."""

    def __init__(
        self,
        environment: str | None = None,
        log_level: str | int = logging.INFO,
        log_dir: str | Path | None = None,
        enable_file_logging: bool = True,
        enable_console_logging: bool = True,
        enable_json_logging: bool | None = None,
        max_file_size: int = DEFAULT_MAX_LOG_FILE_SIZE_BYTES,
        backup_count: int = 10,
        correlation_id_enabled: bool = True,
    ):

        # Executable entry points pass the environment explicitly (asgi/server/cli/
        # tracking/live/analytics); no implicit environment-variable fallback.
        self.environment = environment or "development"
        self.log_level = self._parse_log_level(log_level)
        self.log_dir = Path(log_dir) if log_dir else Path.cwd() / "logs"
        self.enable_file_logging = enable_file_logging
        self.enable_console_logging = enable_console_logging
        self.enable_json_logging = (
            enable_json_logging if enable_json_logging is not None else (self.environment == "production")
        )
        self.max_file_size = max_file_size
        self.backup_count = backup_count
        self.correlation_id_enabled = correlation_id_enabled

        self._ensure_log_directory()

    def _parse_log_level(self, level: str | int) -> int:
        if isinstance(level, str):
            return getattr(logging, level.upper(), logging.INFO)
        return level

    def _ensure_log_directory(self) -> None:
        if self.enable_file_logging:
            try:
                self.log_dir.mkdir(parents=True, exist_ok=True)
                test_file = self.log_dir / ".write_test"
                test_file.touch()
                test_file.unlink()
            except PermissionError, OSError:
                fallback_dir = Path.home() / ".stream_sniper_logs"
                fallback_dir.mkdir(parents=True, exist_ok=True)
                self.log_dir = fallback_dir
                print(f"Warning: Could not write to {self.log_dir}, using fallback: {fallback_dir}")

    def configure_logging(
        self, loggers: dict[str, str | int] | None = None, disable_existing_loggers: bool = False
    ) -> logging.Logger:
        """Configure logging, replacing handlers owned by this package."""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        self._remove_handlers(root_logger, disable_existing_loggers)
        correlation_filter = CorrelationIDFilter() if self.correlation_id_enabled else None

        if self.enable_console_logging:
            root_logger.addHandler(self._console_handler(correlation_filter))
        if self.enable_file_logging:
            for handler in self._file_handlers(correlation_filter):
                root_logger.addHandler(handler)

        self._configure_named_loggers(loggers)
        self._configure_third_party_loggers()
        return root_logger

    @staticmethod
    def _remove_handlers(
        root_logger: logging.Logger,
        disable_existing_loggers: bool,
    ) -> None:
        """Remove handlers owned by this package, or every handler on request."""
        for handler in root_logger.handlers[:]:
            if disable_existing_loggers or getattr(handler, "_stream_sniper_owned", False):
                root_logger.removeHandler(handler)
                handler.close()

    def _console_handler(
        self,
        correlation_filter: CorrelationIDFilter | None,
    ) -> logging.Handler:
        handler = logging.StreamHandler(sys.stdout)
        handler._stream_sniper_owned = True  # type: ignore[attr-defined]
        formatter = JSONFormatter() if self.enable_json_logging else ColoredConsoleFormatter()
        handler.setFormatter(formatter)
        handler.setLevel(self.log_level)
        if correlation_filter:
            handler.addFilter(correlation_filter)
        return handler

    def _file_formatter(self) -> logging.Formatter:
        if self.enable_json_logging:
            return JSONFormatter()
        return logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)s:%(lineno)-4d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )

    def _file_handlers(
        self,
        correlation_filter: CorrelationIDFilter | None,
    ) -> tuple[logging.Handler, logging.Handler]:
        formatter = self._file_formatter()
        app_handler = self._rotating_handler("stream_sniper.log", self.log_level, formatter)
        error_handler = self._rotating_handler("stream_sniper_errors.log", logging.ERROR, formatter)
        if correlation_filter:
            app_handler.addFilter(correlation_filter)
            error_handler.addFilter(correlation_filter)
        return app_handler, error_handler

    def _rotating_handler(
        self,
        filename: str,
        level: int,
        formatter: logging.Formatter,
    ) -> logging.Handler:
        handler = logging.handlers.RotatingFileHandler(
            self.log_dir / filename,
            maxBytes=self.max_file_size,
            backupCount=self.backup_count,
            encoding="utf-8",
        )
        handler._stream_sniper_owned = True  # type: ignore[attr-defined]
        handler.setLevel(level)
        handler.setFormatter(formatter)
        return handler

    def _configure_named_loggers(
        self,
        loggers: dict[str, str | int] | None,
    ) -> None:
        for logger_name, level in (loggers or {}).items():
            logging.getLogger(logger_name).setLevel(self._parse_log_level(level))

    def _configure_third_party_loggers(self) -> None:
        """Configure third-party library loggers to reduce noise."""
        third_party_configs = {
            "urllib3.connectionpool": logging.WARNING,
            "requests.packages.urllib3.connectionpool": logging.WARNING,
            "botocore": logging.WARNING,
            "psycopg2": logging.WARNING,
            "asyncio": logging.WARNING,
            "httpx": logging.WARNING,
            "uvicorn.access": logging.WARNING,
        }

        for logger_name, level in third_party_configs.items():
            logging.getLogger(logger_name).setLevel(level)

    def get_logger(self, name: str) -> logging.Logger:
        return logging.getLogger(name)


_logging_config: LoggingConfig | None = None


def setup_logging(environment: str | None = None, **kwargs: Unpack[LoggingOptions]) -> logging.Logger:
    """Apply the requested process logging configuration.

    Repeated calls replace package-owned handlers and honor the latest explicit
    options. This makes executable entry points authoritative regardless of
    prior imports.
    """
    global _logging_config

    _logging_config = LoggingConfig(environment=environment, **kwargs)
    return _logging_config.configure_logging()


def sanitize_log_value(value: object) -> str:
    """Flatten a user-supplied value for safe log interpolation.

    Escapes CR/LF so request-controlled strings (usernames, search queries,
    titles) cannot forge additional log lines (CodeQL py/log-injection).
    """
    return str(value).replace("\r", "\\r").replace("\n", "\\n")


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger without mutating process logging state."""
    if name is None:
        import inspect

        current_frame = inspect.currentframe()
        caller_frame = current_frame.f_back if current_frame else None
        name = caller_frame.f_globals.get("__name__", "stream_sniper") if caller_frame else "stream_sniper"

    return logging.getLogger(name)


def is_logging_configured() -> bool:
    """Return whether an executable boundary configured package logging."""
    return _logging_config is not None


def get_performance_timer(operation: str, slow_threshold: float = 1.0) -> PerformanceTimer:
    logger = get_logger()
    return PerformanceTimer(logger, operation, slow_threshold=slow_threshold)
