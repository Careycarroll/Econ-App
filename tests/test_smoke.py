"""Smoke tests for the econ_app package.

Uses pytest-qt to create widgets without running the blocking event loop.
"""

from __future__ import annotations


def test_package_imports() -> None:
    """The package can be imported without error."""
    import econ_app

    assert econ_app.__version__ == "0.1.0"


def test_main_window_creates(qtbot) -> None:
    """MainWindow instantiates with the expected title and size."""
    from econ_app.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "Econ-App"
    assert window.size().width() == 1400
    assert window.size().height() == 900


def test_splitter_has_two_panes(qtbot) -> None:
    """The main window's central widget is a splitter with sidebar + content."""
    from econ_app.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    sizes = window.splitter.sizes()
    assert len(sizes) == 2, "Splitter should have exactly two panes"


def test_sidebar_min_max_constraints(qtbot) -> None:
    """The sidebar widget itself enforces min/max widths."""
    from econ_app.ui.main_window import (
        SIDEBAR_MAX_WIDTH,
        SIDEBAR_MIN_WIDTH,
        MainWindow,
    )

    window = MainWindow()
    qtbot.addWidget(window)

    assert window.sidebar.minimumWidth() == SIDEBAR_MIN_WIDTH
    assert window.sidebar.maximumWidth() == SIDEBAR_MAX_WIDTH
