"""Tests for logging_setup and error_handling services."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------- fixtures


@pytest.fixture(autouse=True)
def _clean_logging_state():
    """Ensure each test starts with fresh logging + error-handler state."""
    from econ_app.services import error_handling, logging_setup

    logging_setup._reset_state_for_tests()
    error_handling._reset_state_for_tests()
    yield
    logging_setup._reset_state_for_tests()
    error_handling._reset_state_for_tests()


@pytest.fixture
def isolated_log_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Redirect get_data_dir() to a temp path so log files land in tmp."""
    from econ_app.services import paths

    monkeypatch.setattr(paths, "get_data_dir", lambda: tmp_path)
    return tmp_path


# ---------------------------------------------------------------- logging_setup


def test_configure_logging_creates_log_file(isolated_log_dir: Path) -> None:
    from econ_app.services.logging_setup import configure_logging

    log_path = configure_logging()

    assert log_path.exists() or log_path.parent.exists()
    assert log_path.parent.name == "logs"


def test_configure_logging_is_idempotent(isolated_log_dir: Path) -> None:
    from econ_app.services.logging_setup import configure_logging

    handlers_before = len(logging.getLogger().handlers)

    first = configure_logging()
    handlers_after_first = len(logging.getLogger().handlers)

    second = configure_logging()
    handlers_after_second = len(logging.getLogger().handlers)

    assert first == second
    # First call attaches two handlers (console + rotating file).
    assert handlers_after_first == handlers_before + 2
    # Second call is a no-op; handler count should not grow.
    assert handlers_after_second == handlers_after_first


def test_configure_logging_writes_to_file(isolated_log_dir: Path) -> None:
    from econ_app.services.logging_setup import configure_logging

    log_path = configure_logging()

    logging.getLogger("test_logging").info("hello from a unit test")

    for handler in logging.getLogger().handlers:
        handler.flush()

    contents = log_path.read_text(encoding="utf-8")
    assert "hello from a unit test" in contents


def test_get_log_dir_creates_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from econ_app.services import logging_setup, paths

    subdir = tmp_path / "sub"
    monkeypatch.setattr(paths, "get_data_dir", lambda: subdir)

    result = logging_setup.get_log_dir()

    assert result.exists()
    assert result.is_dir()
    assert result.name == "logs"


# ---------------------------------------------------------------- error_handling


def test_install_handlers_replaces_sys_excepthook() -> None:
    from econ_app.services.error_handling import install_handlers

    original = sys.excepthook

    install_handlers()

    assert sys.excepthook is not original
    assert sys.excepthook.__name__ == "_log_uncaught_exception"


def test_install_handlers_is_idempotent() -> None:
    from econ_app.services.error_handling import install_handlers

    install_handlers()
    first_hook = sys.excepthook

    install_handlers()
    second_hook = sys.excepthook

    assert first_hook is second_hook


def test_uncaught_exception_is_logged(
    isolated_log_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    from econ_app.services.error_handling import _log_uncaught_exception, install_handlers
    from econ_app.services.logging_setup import configure_logging

    configure_logging()
    install_handlers()

    try:
        raise ValueError("simulated crash")
    except ValueError:
        exc_type, exc_value, exc_tb = sys.exc_info()

    with caplog.at_level(logging.CRITICAL, logger="econ_app.services.error_handling"):
        _log_uncaught_exception(exc_type, exc_value, exc_tb)

    assert any("simulated crash" in record.message for record in caplog.records)
    assert any("ValueError" in record.message for record in caplog.records)


def test_keyboard_interrupt_passes_through(isolated_log_dir: Path) -> None:
    """KeyboardInterrupt should not be swallowed; original hook is called."""
    from econ_app.services import error_handling
    from econ_app.services.error_handling import install_handlers

    original_hook = error_handling._original_excepthook

    called = {"count": 0}

    def spy(exc_type, exc_value, exc_tb):
        called["count"] += 1

    error_handling._original_excepthook = spy
    try:
        install_handlers()

        try:
            raise KeyboardInterrupt("user pressed Ctrl+C")
        except KeyboardInterrupt:
            exc_type, exc_value, exc_tb = sys.exc_info()

        sys.excepthook(exc_type, exc_value, exc_tb)

        assert called["count"] == 1
    finally:
        error_handling._original_excepthook = original_hook


def test_threading_exception_handler_logs(
    isolated_log_dir: Path, caplog: pytest.LogCaptureFixture
) -> None:
    from types import SimpleNamespace

    from econ_app.services.error_handling import (
        _log_uncaught_threading_exception,
        install_handlers,
    )
    from econ_app.services.logging_setup import configure_logging

    configure_logging()
    install_handlers()

    try:
        raise RuntimeError("worker died")
    except RuntimeError:
        exc_type, exc_value, exc_tb = sys.exc_info()

    fake_thread = SimpleNamespace(name="ImportWorker-1")
    args = SimpleNamespace(
        exc_type=exc_type,
        exc_value=exc_value,
        exc_traceback=exc_tb,
        thread=fake_thread,
    )

    with caplog.at_level(logging.CRITICAL, logger="econ_app.services.error_handling"):
        _log_uncaught_threading_exception(args)

    assert any("worker died" in record.message for record in caplog.records)
    assert any("ImportWorker-1" in record.message for record in caplog.records)
