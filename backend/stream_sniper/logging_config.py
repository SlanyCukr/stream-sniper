"""
Centralized logging configuration for Stream Sniper.

This module provides structured logging with JSON formatters, correlation IDs,
log rotation, and environment-based configuration.
"""

import contextvars
import json
import logging
import logging.handlers
import os
import sys
import time
import uuid
from contextlib import contextmanager
from functools import wraps
from pathlib import Path
from typing import Any, Dict, Optional, Union

# Context variable for correlation ID
correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="")


class CorrelationIDFilter(logging.Filter):
    """Add correlation ID to log records."""

    def filter(self, record):
        record.correlation_id = correlation_id_var.get("")
        return True


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def __init__(self, include_extra_fields: bool = True):
        super().__init__()
        self.include_extra_fields = include_extra_fields

    def format(self, record: logging.LogRecord) -> str:
        # Base log fields
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation ID if present
        correlation_id = getattr(record, "correlation_id", "")
        if correlation_id:
            log_data["correlation_id"] = correlation_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if enabled
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
    """Colored console formatter for development."""

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
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        self.logger.log(self.level, f"Starting {self.operation}")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
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


def performance_timer(operation: str = None, slow_threshold: float = 1.0):
    """Decorator for measuring function performance."""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            logger = logging.getLogger(func.__module__)
            op_name = operation or f"{func.__name__}"

            with PerformanceTimer(logger, op_name, slow_threshold=slow_threshold):
                return func(*args, **kwargs)

        return wrapper

    return decorator


@contextmanager
def correlation_context(correlation_id: str = None):
    """Context manager for setting correlation ID."""
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())

    token = correlation_id_var.set(correlation_id)
    try:
        yield correlation_id
    finally:
        correlation_id_var.reset(token)


def get_correlation_id() -> str:
    """Get current correlation ID."""
    return correlation_id_var.get("")


def set_correlation_id(correlation_id: str):
    """Set correlation ID for current context."""
    correlation_id_var.set(correlation_id)


class LoggingConfig:
    """Centralized logging configuration."""

    def __init__(
        self,
        environment: str = None,
        log_level: Union[str, int] = logging.INFO,
        log_dir: Union[str, Path] = None,
        enable_file_logging: bool = True,
        enable_console_logging: bool = True,
        enable_json_logging: bool = None,
        max_file_size: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 10,
        correlation_id_enabled: bool = True,
    ):

        self.environment = environment or os.getenv("ENVIRONMENT", "development")
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

    def _parse_log_level(self, level: Union[str, int]) -> int:
        """Parse log level from string or int."""
        if isinstance(level, str):
            return getattr(logging, level.upper(), logging.INFO)
        return level

    def _ensure_log_directory(self):
        """Ensure log directory exists."""
        if self.enable_file_logging:
            try:
                self.log_dir.mkdir(parents=True, exist_ok=True)
                # Test write permissions
                test_file = self.log_dir / ".write_test"
                test_file.touch()
                test_file.unlink()
            except (PermissionError, OSError) as e:
                # Fallback to user's home directory
                import os

                fallback_dir = Path.home() / ".stream_sniper_logs"
                fallback_dir.mkdir(parents=True, exist_ok=True)
                self.log_dir = fallback_dir
                print(f"Warning: Could not write to {self.log_dir}, using fallback: {fallback_dir}")

    def configure_logging(
        self, loggers: Optional[Dict[str, Union[str, int]]] = None, disable_existing_loggers: bool = False
    ) -> logging.Logger:
        """Configure logging system."""

        # Create root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)

        # Clear existing handlers if requested
        if disable_existing_loggers:
            for handler in root_logger.handlers[:]:
                root_logger.removeHandler(handler)

        # Add correlation ID filter if enabled
        correlation_filter = CorrelationIDFilter() if self.correlation_id_enabled else None

        # Configure console logging
        if self.enable_console_logging:
            console_handler = logging.StreamHandler(sys.stdout)

            if self.enable_json_logging:
                console_formatter = JSONFormatter()
            else:
                console_formatter = ColoredConsoleFormatter()

            console_handler.setFormatter(console_formatter)
            console_handler.setLevel(self.log_level)

            if correlation_filter:
                console_handler.addFilter(correlation_filter)

            root_logger.addHandler(console_handler)

        # Configure file logging
        if self.enable_file_logging:
            # Main application log
            app_log_file = self.log_dir / "stream_sniper.log"
            file_handler = logging.handlers.RotatingFileHandler(
                app_log_file, maxBytes=self.max_file_size, backupCount=self.backup_count, encoding="utf-8"
            )

            if self.enable_json_logging:
                file_formatter = JSONFormatter()
            else:
                file_formatter = logging.Formatter(
                    "%(asctime)s | %(levelname)-8s | %(name)-20s | %(funcName)s:%(lineno)-4d | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )

            file_handler.setFormatter(file_formatter)
            file_handler.setLevel(self.log_level)

            if correlation_filter:
                file_handler.addFilter(correlation_filter)

            root_logger.addHandler(file_handler)

            # Error log (only ERROR and CRITICAL)
            error_log_file = self.log_dir / "stream_sniper_errors.log"
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file, maxBytes=self.max_file_size, backupCount=self.backup_count, encoding="utf-8"
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(file_formatter)

            if correlation_filter:
                error_handler.addFilter(correlation_filter)

            root_logger.addHandler(error_handler)

        # Configure specific loggers
        if loggers:
            for logger_name, level in loggers.items():
                logger = logging.getLogger(logger_name)
                logger.setLevel(self._parse_log_level(level))

        # Configure third-party loggers to reduce noise
        self._configure_third_party_loggers()

        return root_logger

    def _configure_third_party_loggers(self):
        """Configure third-party library loggers to reduce noise."""
        third_party_configs = {
            "urllib3.connectionpool": logging.WARNING,
            "requests.packages.urllib3.connectionpool": logging.WARNING,
            "botocore": logging.WARNING,
            "psycopg2": logging.WARNING,
            "redis": logging.WARNING,
            "asyncio": logging.WARNING,
            "httpx": logging.WARNING,
            "uvicorn.access": logging.WARNING,
        }

        for logger_name, level in third_party_configs.items():
            logging.getLogger(logger_name).setLevel(level)

    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with the given name."""
        return logging.getLogger(name)


# Global logging configuration instance
_logging_config: Optional[LoggingConfig] = None


def setup_logging(environment: str = None, **kwargs) -> logging.Logger:
    """Setup logging configuration globally."""
    global _logging_config

    if _logging_config is None:
        _logging_config = LoggingConfig(environment=environment, **kwargs)

    return _logging_config.configure_logging()


def get_logger(name: str = None) -> logging.Logger:
    """Get a logger instance."""
    if _logging_config is None:
        # Initialize with defaults if not configured
        setup_logging()

    if name is None:
        # Get the calling module's name
        import inspect

        frame = inspect.currentframe().f_back
        name = frame.f_globals.get("__name__", "stream_sniper")

    return logging.getLogger(name)


# Convenience functions
def get_performance_timer(operation: str, slow_threshold: float = 1.0) -> PerformanceTimer:
    """Get a performance timer context manager."""
    logger = get_logger()
    return PerformanceTimer(logger, operation, slow_threshold=slow_threshold)
