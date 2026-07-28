"""Configure logging for the Econ-App.

Two handlers are attached to the root logger:

- Console handler writes INFO+ to stderr for interactive runs.
- Rotating file handler writes DEBUG+ to a log file inside the platform
  data directory, so packaged / headless runs still leave a diagnostic trail.

Call configure_logging() once at app startup, before creating the QApplication.
Repeated calls in the same process are no-ops.
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from econ_app.services.paths import get_data_dir

LOG_FILE_NAME = "econ_app.log"
LOG_DIR_NAME = "logs"

# 5 MB per file, keep 5 backups.
_ROTATE_MAX_BYTES = 5 * 1024 * 1024
_ROTATE_BACKUP_COUNT = 5

_CONSOLE_FORMAT = "%(asctime)s %(levelname)-7s %(name)-40s %(message)s"
_CONSOLE_DATEFMT = "%H:%M:%S"
_FILE_FORMAT = "%(asctime)s.%(msecs)03d %(levelname)-7s %(name)-40s %(threadName)s %(message)s"
_FILE_DATEFMT = "%Y-%m-%d %H:%M:%S"

_configured = False


def get_log_dir() -> Path:
    """Return the directory that holds Econ-App log files, creating it if needed."""
    data_dir = get_data_dir()
    log_dir = data_dir / LOG_DIR_NAME
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def get_log_file() -> Path:
    """Return the primary log file path."""
    return get_log_dir() / LOG_FILE_NAME


def configure_logging(
    console_level: int | None = None,
    file_level: int = logging.DEBUG,
    log_file: Path | None = None,
) -> Path:
    """Attach console + rotating-file handlers to the root logger.

    Safe to call more than once; subsequent calls short-circuit.

    Args:
        console_level: Level for the stderr handler. Defaults to $ECON_APP_LOG_LEVEL
            if set, otherwise INFO.
        file_level: Level for the file handler. Defaults to DEBUG so on-disk logs
            always carry full detail.
        log_file: Override for the file location; used by tests.

    Returns:
        Path to the log file that was configured.
    """
    global _configured

    if console_level is None:
        raw = os.environ.get("ECON_APP_LOG_LEVEL", "INFO").upper()
        console_level = getattr(logging, raw, logging.INFO)

    target_file = log_file if log_file is not None else get_log_file()

    root = logging.getLogger()

    if _configured:
        return target_file

    # Root captures everything; handlers filter below.
    root.setLevel(logging.DEBUG)

    # ------------------------------------------------------------ console
    console = logging.StreamHandler(stream=sys.stderr)
    console.setLevel(console_level)
    console.setFormatter(logging.Formatter(_CONSOLE_FORMAT, datefmt=_CONSOLE_DATEFMT))
    root.addHandler(console)

    # ------------------------------------------------------------ file
    file_handler = RotatingFileHandler(
        target_file,
        maxBytes=_ROTATE_MAX_BYTES,
        backupCount=_ROTATE_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(file_level)
    file_handler.setFormatter(logging.Formatter(_FILE_FORMAT, datefmt=_FILE_DATEFMT))
    root.addHandler(file_handler)

    # Quiet a few known-noisy libraries so they don't drown out our own logs.
    for noisy in ("PIL", "urllib3", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    _configured = True

    logging.getLogger(__name__).info(
        "Logging configured. Console=%s, file=%s (level %s), log=%s",
        logging.getLevelName(console_level),
        logging.getLevelName(file_level),
        logging.getLevelName(file_level),
        target_file,
    )

    return target_file


def _reset_state_for_tests() -> None:
    """Drop cached configuration flag and clear root handlers.

    Only intended for use inside the test suite so each test can call
    configure_logging() against a temporary directory.
    """
    global _configured
    _configured = False
    root = logging.getLogger()
    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()
