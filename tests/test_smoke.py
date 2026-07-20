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


def test_toggle_button_exists(qtbot) -> None:
    """The toggle button exists as a child of the main window."""
    from econ_app.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    assert window.toggle_button is not None
    assert window.toggle_button.parent() is window


def test_toggle_sidebar_hides_and_shows(qtbot) -> None:
    """Calling toggle_sidebar() hides the sidebar, then shows it again."""
    from econ_app.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    assert window.sidebar.isHidden() is False

    window.toggle_sidebar()
    assert window.sidebar.isHidden() is True

    window.toggle_sidebar()
    assert window.sidebar.isHidden() is False


def test_menu_bar_has_expected_menus(qtbot) -> None:
    """The menu bar contains all 5 expected top-level menus in order."""
    from econ_app.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    menubar = window.menuBar()
    titles = [action.text() for action in menubar.actions()]

    assert titles == [
        "Econ-App",
        "View",
        "Data",
        "Window",
        "Help",
    ], f"Unexpected menu titles: {titles}"


def test_view_menu_has_view_switch_actions(qtbot) -> None:
    """The View menu contains the four view-switch actions."""
    from econ_app.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    menubar = window.menuBar()
    view_menu = next((a.menu() for a in menubar.actions() if a.text() == "View"), None)
    assert view_menu is not None, "View menu not found"

    view_names = [a.text() for a in view_menu.actions() if not a.isSeparator() and a.text()]
    for expected in ["Calendar", "Explorer", "Series Detail", "Core Indicators"]:
        assert expected in view_names, f"Missing view action: {expected}"
