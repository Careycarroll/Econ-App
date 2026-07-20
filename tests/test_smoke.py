"""Smoke tests for the econ_app package.

Uses pytest-qt to create the window without running the blocking event loop.
"""

from __future__ import annotations


def test_package_imports() -> None:
    """The package can be imported without error."""
    import econ_app

    assert econ_app.__version__ == "0.1.0"


def test_main_window_creates(qtbot) -> None:
    """MainWindow instantiates with the expected title and size."""
    from econ_app.app import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "Econ-App"
    assert window.size().width() == 1400
    assert window.size().height() == 900
