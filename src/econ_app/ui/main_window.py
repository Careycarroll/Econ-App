"""Main window for Econ-App.

Per Issue #15, the central widget is a QSplitter with a sidebar
(280px default, 200-400px range) and a content area.

Per Issue #16, the sidebar is toggleable via a button (top-left of the
main window). Open/closed state and width persist across sessions.

Per Issue #17, the app has a menu bar with 5 menus (Econ-App/File, View,
Data, Window, Help) and all keyboard shortcuts registered. Most action
handlers are placeholders — real functionality lands in later issues.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QMainWindow,
    QMenu,
    QMenuBar,
    QPushButton,
    QSplitter,
    QWidget,
)

SIDEBAR_MIN_WIDTH = 200
SIDEBAR_MAX_WIDTH = 400
SIDEBAR_DEFAULT_WIDTH = 280
WINDOW_DEFAULT_WIDTH = 1400
WINDOW_DEFAULT_HEIGHT = 900

TOGGLE_BUTTON_SIZE = 32


def _todo(msg: str) -> None:
    """Placeholder logger for menu actions not yet implemented."""
    print(f"[TODO] {msg}", file=sys.stderr)


class MainWindow(QMainWindow):
    """The application's main window.

    Layout: horizontal QSplitter with sidebar (left) and content area (right).
    Toggle button (top-left, floating) and Cmd+\\ shortcut hide/show the sidebar.
    Menu bar (top of screen on macOS, in-window elsewhere) provides all app-level
    actions and keyboard shortcuts.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Econ-App")
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)

        self._settings = QSettings()

        self.sidebar = self._build_sidebar()
        self.content_area = self._build_content_area()

        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.content_area)
        self.splitter.setHandleWidth(4)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        self.setCentralWidget(self.splitter)

        # Floating toggle button parented to the main window so it stays visible
        # when the sidebar is hidden.
        self.toggle_button = QPushButton("\u2630", self)
        self.toggle_button.setFixedSize(TOGGLE_BUTTON_SIZE, TOGGLE_BUTTON_SIZE)
        self.toggle_button.setToolTip("Toggle sidebar (Cmd+\\)")
        self.toggle_button.setStyleSheet(
            "QPushButton { background-color: rgba(255, 255, 255, 200); "
            "border: 1px solid #d0d0d0; border-radius: 4px; font-size: 16px; }"
            "QPushButton:hover { background-color: rgba(240, 240, 240, 220); }"
        )
        self.toggle_button.clicked.connect(self.toggle_sidebar)
        self.toggle_button.move(8, 8)
        self.toggle_button.raise_()

        # Menu bar (must be built after other widgets so actions can reference them)
        self._build_menu_bar()

        self._restore_state()
        self.splitter.splitterMoved.connect(self._on_splitter_moved)

    # ---------------------------------------------------------------- layout

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(SIDEBAR_MIN_WIDTH)
        sidebar.setMaximumWidth(SIDEBAR_MAX_WIDTH)
        sidebar.setStyleSheet(
            "#sidebar { background-color: #f0f0f0; border-right: 1px solid #d0d0d0; }"
        )
        return sidebar

    def _build_content_area(self) -> QWidget:
        content = QFrame()
        content.setObjectName("content")
        content.setStyleSheet("#content { background-color: #ffffff; }")
        return content

    # ------------------------------------------------------------- menu bar

    def _build_menu_bar(self) -> None:
        """Construct the full menu bar per ADR-0003."""
        menubar: QMenuBar = self.menuBar()

        self._build_app_menu(menubar)
        self._build_view_menu(menubar)
        self._build_data_menu(menubar)
        self._build_window_menu(menubar)
        self._build_help_menu(menubar)

    def _build_app_menu(self, menubar: QMenuBar) -> None:
        """Econ-App menu (macOS) / File menu (Win/Linux).

        On macOS, actions with certain roles (About, Preferences, Quit) are
        automatically moved to the application menu by Qt.
        """
        menu: QMenu = menubar.addMenu("Econ-App")

        about_action = QAction("About Econ-App", self)
        about_action.setMenuRole(QAction.MenuRole.AboutRole)
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)

        prefs_action = QAction("Preferences...", self)
        prefs_action.setShortcut(QKeySequence("Ctrl+,"))
        prefs_action.setMenuRole(QAction.MenuRole.PreferencesRole)
        prefs_action.triggered.connect(lambda: _todo("Preferences dialog — coming in Issue #19"))
        menu.addAction(prefs_action)

        menu.addSeparator()

        quit_action = QAction("Quit Econ-App", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.setMenuRole(QAction.MenuRole.QuitRole)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

    def _build_view_menu(self, menubar: QMenuBar) -> None:
        menu: QMenu = menubar.addMenu("View")

        # View switching (Cmd+1..4) — placeholders until Issue #18
        for i, name in enumerate(
            ["Calendar", "Explorer", "Series Detail", "Core Indicators"], start=1
        ):
            action = QAction(name, self)
            action.setShortcut(QKeySequence(f"Ctrl+{i}"))
            action.setCheckable(True)
            if i == 1:  # Calendar is the default per ADR-0003
                action.setChecked(True)
            # Close over the name explicitly to avoid the loop-variable trap
            action.triggered.connect(lambda _checked=False, n=name: _todo(f"Switch to {n} view"))
            menu.addAction(action)

        menu.addSeparator()

        toggle_sidebar_action = QAction("Toggle Sidebar", self)
        toggle_sidebar_action.setShortcut(QKeySequence("Ctrl+\\"))
        toggle_sidebar_action.triggered.connect(self.toggle_sidebar)
        menu.addAction(toggle_sidebar_action)

        focus_mode_action = QAction("Focus Mode", self)
        focus_mode_action.setShortcut(QKeySequence("Ctrl+Shift+F"))
        focus_mode_action.triggered.connect(lambda: _todo("Focus Mode — coming in Issue #67"))
        menu.addAction(focus_mode_action)

        menu.addSeparator()

        zoom_in = QAction("Zoom In", self)
        zoom_in.setShortcut(QKeySequence("Ctrl++"))
        zoom_in.triggered.connect(lambda: _todo("Zoom In — coming in Issue #66"))
        menu.addAction(zoom_in)

        zoom_reset = QAction("Reset Zoom", self)
        zoom_reset.setShortcut(QKeySequence("Ctrl+0"))
        zoom_reset.triggered.connect(lambda: _todo("Reset Zoom — coming in Issue #66"))
        menu.addAction(zoom_reset)

        zoom_out = QAction("Zoom Out", self)
        zoom_out.setShortcut(QKeySequence("Ctrl+-"))
        zoom_out.triggered.connect(lambda: _todo("Zoom Out — coming in Issue #66"))
        menu.addAction(zoom_out)

    def _build_data_menu(self, menubar: QMenuBar) -> None:
        menu: QMenu = menubar.addMenu("Data")

        refresh_all = QAction("Refresh All", self)
        refresh_all.setShortcut(QKeySequence("Ctrl+R"))
        refresh_all.triggered.connect(lambda: _todo("Refresh All — coming in v0.3 (FRED client)"))
        menu.addAction(refresh_all)

        refresh_current = QAction("Refresh Current Series", self)
        refresh_current.triggered.connect(lambda: _todo("Refresh Current — coming in v0.3"))
        menu.addAction(refresh_current)

        menu.addSeparator()

        open_folder = QAction("Open Data Folder", self)
        open_folder.triggered.connect(lambda: _todo("Open Data Folder — coming in v0.3"))
        menu.addAction(open_folder)

    def _build_window_menu(self, menubar: QMenuBar) -> None:
        menu: QMenu = menubar.addMenu("Window")

        minimize = QAction("Minimize", self)
        minimize.setShortcut(QKeySequence("Ctrl+M"))
        minimize.triggered.connect(self.showMinimized)
        menu.addAction(minimize)

        zoom = QAction("Zoom", self)
        zoom.triggered.connect(self._toggle_maximized)
        menu.addAction(zoom)

    def _build_help_menu(self, menubar: QMenuBar) -> None:
        menu: QMenu = menubar.addMenu("Help")

        fred_docs = QAction("FRED Documentation", self)
        fred_docs.triggered.connect(
            lambda: _todo("Open https://fred.stlouisfed.org/docs/api/fred/")
        )
        menu.addAction(fred_docs)

        about_series = QAction("About FRED Series IDs", self)
        about_series.triggered.connect(lambda: _todo("About FRED Series IDs — help content TBD"))
        menu.addAction(about_series)

        menu.addSeparator()

        report_issue = QAction("Report Issue", self)
        report_issue.triggered.connect(
            lambda: _todo("Open https://github.com/Careycarroll/Econ-App/issues")
        )
        menu.addAction(report_issue)

    # ---------------------------------------------------------------- actions

    def _show_about(self) -> None:
        """Show the About dialog. Delegates to app module for the dialog itself."""
        from econ_app.app import show_about_dialog

        show_about_dialog(self)

    def _toggle_maximized(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def toggle_sidebar(self) -> None:
        """Show or hide the sidebar; persist the new state."""
        if not self.sidebar.isHidden():
            current_width = self.splitter.sizes()[0]
            if current_width > 0:
                self._settings.setValue("mainwindow/sidebar_width", current_width)
            self.sidebar.setVisible(False)
            self._settings.setValue("mainwindow/sidebar_open", False)
        else:
            self.sidebar.setVisible(True)
            saved_width = self._settings.value(
                "mainwindow/sidebar_width", SIDEBAR_DEFAULT_WIDTH, type=int
            )
            width = max(SIDEBAR_MIN_WIDTH, min(SIDEBAR_MAX_WIDTH, saved_width))
            total = self.splitter.width()
            self.splitter.setSizes([width, max(0, total - width)])
            self._settings.setValue("mainwindow/sidebar_open", True)

    def _restore_state(self) -> None:
        saved_width = self._settings.value(
            "mainwindow/sidebar_width", SIDEBAR_DEFAULT_WIDTH, type=int
        )
        width = max(SIDEBAR_MIN_WIDTH, min(SIDEBAR_MAX_WIDTH, saved_width))
        self.splitter.setSizes([width, WINDOW_DEFAULT_WIDTH - width])

        is_open = self._settings.value("mainwindow/sidebar_open", True, type=bool)
        self.sidebar.setVisible(is_open)

    def _on_splitter_moved(self, _pos: int, _index: int) -> None:
        sizes = self.splitter.sizes()
        if sizes and sizes[0] > 0:
            self._settings.setValue("mainwindow/sidebar_width", sizes[0])

    def sidebar_width(self) -> int:
        return self.splitter.sizes()[0]
