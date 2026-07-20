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


def test_menu_bar_has_five_menus(qtbot) -> None:
    """The menu bar contains the 5 expected top-level menus."""
    from econ_app.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    menubar = window.menuBar()
    titles = [a.text() for a in menubar.actions()]
    assert titles == [
        "Econ-App",
        "View",
        "Data",
        "Window",
        "Help",
    ], f"Unexpected menu titles: {titles}"


def test_view_switching_updates_current_view(qtbot) -> None:
    """switch_view() changes the visible view and updates menu checkmark."""
    from econ_app.ui.main_window import MainWindow

    window = MainWindow()
    qtbot.addWidget(window)

    # Force My Calendar as starting view (settings may have persisted a different view)
    window.switch_view("My Calendar")
    my_calendar_widget = window._views["My Calendar"]
    assert window.content_stack.currentWidget() is my_calendar_widget

    # Switch to Explorer
    window.switch_view("Explorer")
    explorer_widget = window._views["Explorer"]
    assert window.content_stack.currentWidget() is explorer_widget

    # Menu checkmark should follow
    assert window._view_actions["Explorer"].isChecked() is True


def test_preferences_dialog_opens(qtbot) -> None:
    """PreferencesDialog instantiates with 3 tabs."""
    from econ_app.ui.preferences_dialog import PreferencesDialog

    dialog = PreferencesDialog()
    qtbot.addWidget(dialog)

    # Find the QTabWidget inside
    from PySide6.QtWidgets import QTabWidget

    tabs = dialog.findChild(QTabWidget)
    assert tabs is not None
    assert tabs.count() == 3
    assert [tabs.tabText(i) for i in range(3)] == ["General", "Appearance", "Advanced"]


def test_market_calendar_view_instantiates(qtbot) -> None:
    """MarketCalendarView creates without error and has a web view or fallback widget."""
    from econ_app.ui.views.placeholders import MarketCalendarView

    view = MarketCalendarView()
    qtbot.addWidget(view)

    # Either QWebEngineView loaded or the fallback label is present
    assert view._web_view is not None
