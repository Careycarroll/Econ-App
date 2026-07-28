"""Install app-wide error handlers.

Two handlers are attached:

- sys.excepthook: catches uncaught Python exceptions on the main thread and
  logs the full traceback before the app dies. Without this, PyQt swallows
  the traceback and the app disappears with no explanation.

- Qt message handler: routes Qt's own warnings and critical/fatal messages
  through Python logging so they show up in the log file alongside app logs.

Call install_handlers() once at app startup, after configure_logging() has
attached the file handler but before creating the QApplication.
"""

from __future__ import annotations

import logging
import sys
import threading
import traceback
from types import TracebackType

log = logging.getLogger(__name__)

_installed = False

# Preserve the original excepthook so we can restore it during tests and
# still call it as a fallback if something goes wrong inside our handler.
_original_excepthook = sys.excepthook


def _log_uncaught_exception(
    exc_type: type[BaseException],
    exc_value: BaseException,
    exc_traceback: TracebackType | None,
) -> None:
    """Log an uncaught exception. Installed as sys.excepthook."""
    if issubclass(exc_type, KeyboardInterrupt):
        # Let Ctrl+C behave normally in headless / CLI runs.
        _original_excepthook(exc_type, exc_value, exc_traceback)
        return

    log.critical(
        "Uncaught %s on main thread: %s\n%s",
        exc_type.__name__,
        exc_value,
        "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
    )


def _log_uncaught_threading_exception(args) -> None:
    """Log an uncaught exception in a worker thread. Installed as threading.excepthook."""
    exc_type = args.exc_type
    exc_value = args.exc_value
    exc_traceback = args.exc_traceback
    thread = args.thread

    if issubclass(exc_type, SystemExit):
        return

    log.critical(
        "Uncaught %s in thread %s: %s\n%s",
        exc_type.__name__,
        thread.name if thread else "<unknown>",
        exc_value,
        "".join(traceback.format_exception(exc_type, exc_value, exc_traceback)),
    )


def _install_qt_handler() -> None:
    """Route Qt's own warnings/critical/fatal messages into Python logging.

    Qt has its own message system for library-internal warnings (paint issues,
    layout warnings, etc). Without this handler they go to stderr only and
    won't show up in the app log file.
    """
    try:
        from PySide6.QtCore import QtMsgType, qInstallMessageHandler
    except ImportError:
        # In headless / test runs without Qt installed, silently skip.
        log.debug("Qt not available; skipping Qt message handler install.")
        return

    qt_logger = logging.getLogger("Qt")

    def handler(mode, context, message) -> None:
        source = ""
        if context is not None:
            file_ = getattr(context, "file", None)
            line = getattr(context, "line", None)
            if file_:
                source = f" ({file_}:{line})" if line else f" ({file_})"

        if mode == QtMsgType.QtDebugMsg:
            qt_logger.debug("%s%s", message, source)
        elif mode == QtMsgType.QtInfoMsg:
            qt_logger.info("%s%s", message, source)
        elif mode == QtMsgType.QtWarningMsg:
            qt_logger.warning("%s%s", message, source)
        elif mode == QtMsgType.QtCriticalMsg:
            qt_logger.error("%s%s", message, source)
        elif mode == QtMsgType.QtFatalMsg:
            qt_logger.critical("Qt fatal: %s%s", message, source)
        else:
            qt_logger.warning("Qt (unknown level): %s%s", message, source)

    qInstallMessageHandler(handler)


def install_handlers() -> None:
    """Install sys.excepthook, threading.excepthook, and Qt message handler.

    Safe to call more than once; subsequent calls short-circuit.
    """
    global _installed
    if _installed:
        return

    sys.excepthook = _log_uncaught_exception

    # threading.excepthook was added in 3.8; guard just in case.
    if hasattr(threading, "excepthook"):
        threading.excepthook = _log_uncaught_threading_exception

    _install_qt_handler()

    _installed = True
    log.info("Global error handlers installed.")


def _reset_state_for_tests() -> None:
    """Restore original hooks so tests can install handlers repeatedly."""
    global _installed
    sys.excepthook = _original_excepthook
    _installed = False
