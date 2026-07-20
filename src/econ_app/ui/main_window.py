"""Main window for Econ-App.

Per Issue #15: QSplitter shell.
Per Issue #16: toggleable sidebar with persistent state.
Per Issue #17: menu bar with 5 menus.
Per Issue #18: view switcher with 4 placeholder views (QStackedWidget).
Per Issue #19: Preferences dialog wired to menu action.
"""

from __future__ import annotations

import sys

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QMainWindow,
    QMenu,
    QMenuBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from econ_app.ui.preferences_dialog import PreferencesDialog
from econ_app.ui.views.my_calendar import MyCalendarView
from econ_app.ui.views.placeholders import (
    CoreIndicatorsView,
    ExplorerView,
    MarketCalendarView,
    SeriesDetailView,
)

SIDEBAR_MIN_WIDTH = 200
SIDEBAR_MAX_WIDTH = 400
SIDEBAR_DEFAULT_WIDTH = 280
WINDOW_DEFAULT_WIDTH = 1400
WINDOW_DEFAULT_HEIGHT = 900

TOGGLE_BUTTON_SIZE = 32


def _todo(msg: str) -> None:
    """Placeholder logger for actions not yet implemented."""
    print(f"[TODO] {msg}", file=sys.stderr)


class MainWindow(QMainWindow):
    """Main application window with view switcher, contextual sidebar, and menu bar."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Econ-App")
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)

        self._settings = QSettings()

        # Instantiate views
        self._views: dict[str, QWidget] = {
            "My Calendar": MyCalendarView(),
            "Explorer": ExplorerView(),
            "Series Detail": SeriesDetailView(),
            "Core Indicators": CoreIndicatorsView(),
            "Market Calendar": MarketCalendarView(),
        }
        self._view_actions: dict[str, QAction] = {}

        # Sidebar (with a layout so we can swap contextual content)
        self.sidebar = self._build_sidebar()
        # Content area is a QStackedWidget holding all views
        self.content_stack = QStackedWidget()
        for view in self._views.values():
            self.content_stack.addWidget(view)

        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.addWidget(self.sidebar)
        self.splitter.addWidget(self.content_stack)
        self.splitter.setHandleWidth(4)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)
        self.setCentralWidget(self.splitter)

        # Floating toggle button (parented to window so it persists when sidebar hides)
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

        # Menu bar
        self._build_menu_bar()

        # Restore state and set initial view
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
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, TOGGLE_BUTTON_SIZE + 16, 8, 8)
        layout.setSpacing(4)
        sidebar.setLayout(layout)
        return sidebar

    def _set_sidebar_content(self, widget: QWidget) -> None:
        """Replace whatever is currently in the sidebar with the given widget."""
        layout = self.sidebar.layout()
        # Remove existing children (except keep the layout itself)
        while layout.count():
            item = layout.takeAt(0)
            existing = item.widget()
            if existing is not None:
                existing.setParent(None)
        layout.addWidget(widget)
        layout.addStretch(1)

    # ------------------------------------------------------------- menu bar

    def _build_menu_bar(self) -> None:
        menubar: QMenuBar = self.menuBar()
        self._build_app_menu(menubar)
        self._build_view_menu(menubar)
        self._build_data_menu(menubar)
        self._build_window_menu(menubar)
        self._build_help_menu(menubar)

    def _build_app_menu(self, menubar: QMenuBar) -> None:
        menu: QMenu = menubar.addMenu("Econ-App")

        about_action = QAction("About Econ-App", self)
        about_action.setMenuRole(QAction.MenuRole.AboutRole)
        about_action.triggered.connect(self._show_about)
        menu.addAction(about_action)

        prefs_action = QAction("Preferences...", self)
        prefs_action.setShortcut(QKeySequence("Ctrl+,"))
        prefs_action.setMenuRole(QAction.MenuRole.PreferencesRole)
        prefs_action.triggered.connect(self._open_preferences)
        menu.addAction(prefs_action)

        menu.addSeparator()

        quit_action = QAction("Quit Econ-App", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.setMenuRole(QAction.MenuRole.QuitRole)
        quit_action.triggered.connect(QApplication.quit)
        menu.addAction(quit_action)

    def _build_view_menu(self, menubar: QMenuBar) -> None:
        menu: QMenu = menubar.addMenu("View")

        # View switching — checkable, exclusive
        view_group = QActionGroup(self)
        view_group.setExclusive(True)

        for i, name in enumerate(
            ["My Calendar", "Explorer", "Series Detail", "Core Indicators", "Market Calendar"],
            start=1,
        ):
            action = QAction(name, self)
            action.setShortcut(QKeySequence(f"Ctrl+{i}"))
            action.setCheckable(True)
            action.triggered.connect(lambda _checked=False, n=name: self.switch_view(n))
            view_group.addAction(action)
            menu.addAction(action)
            self._view_actions[name] = action

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

        for label, shortcut, todo_msg in [
            ("Zoom In", "Ctrl++", "Zoom In — coming in Issue #66"),
            ("Reset Zoom", "Ctrl+0", "Reset Zoom — coming in Issue #66"),
            ("Zoom Out", "Ctrl+-", "Zoom Out — coming in Issue #66"),
        ]:
            act = QAction(label, self)
            act.setShortcut(QKeySequence(shortcut))
            act.triggered.connect(lambda _checked=False, m=todo_msg: _todo(m))
            menu.addAction(act)

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
        zoom.triggered.connect(self._toggle_zoom)
        menu.addAction(zoom)

    def _build_help_menu(self, menubar: QMenuBar) -> None:
        menu: QMenu = menubar.addMenu("Help")
        fred_docs = QAction("FRED Documentation", self)
        fred_docs.triggered.connect(lambda: _todo("Open FRED docs URL — coming later"))
        menu.addAction(fred_docs)

        fred_ids = QAction("About FRED Series IDs", self)
        fred_ids.triggered.connect(lambda: _todo("About FRED Series IDs — coming later"))
        menu.addAction(fred_ids)

        menu.addSeparator()

        report = QAction("Report Issue", self)
        report.triggered.connect(lambda: _todo("Open GitHub issue URL — coming later"))
        menu.addAction(report)

    # ---------------------------------------------------------------- actions

    def _show_about(self) -> None:
        from econ_app.app import show_about_dialog

        show_about_dialog(self)

    def _open_preferences(self) -> None:
        # TODO(#67): if Focus Mode is active, exit it before showing this dialog
        dialog = PreferencesDialog(self)
        dialog.exec()

    def _toggle_zoom(self) -> None:
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def switch_view(self, name: str) -> None:
        """Switch the visible content view and swap sidebar content to match."""
        if name not in self._views:
            _todo(f"Unknown view: {name}")
            return
        view = self._views[name]
        self.content_stack.setCurrentWidget(view)
        self._set_sidebar_content(view.sidebar_widget)
        # Update menu checkmark
        action = self._view_actions.get(name)
        if action is not None:
            action.setChecked(True)
        # Persist
        self._settings.setValue("mainwindow/current_view", name)

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

    def _on_splitter_moved(self, _pos: int, _index: int) -> None:
        if not self.sidebar.isHidden():
            current_width = self.splitter.sizes()[0]
            if current_width > 0:
                self._settings.setValue("mainwindow/sidebar_width", current_width)

    # -------------------------------------------------------------- state

    def _restore_state(self) -> None:
        saved_width = self._settings.value(
            "mainwindow/sidebar_width", SIDEBAR_DEFAULT_WIDTH, type=int
        )
        width = max(SIDEBAR_MIN_WIDTH, min(SIDEBAR_MAX_WIDTH, saved_width))
        self.splitter.setSizes([width, WINDOW_DEFAULT_WIDTH - width])

        sidebar_open = self._settings.value("mainwindow/sidebar_open", True, type=bool)
        if not sidebar_open:
            self.sidebar.setVisible(False)

        # Restore last-active view (default Calendar)
        last_view = self._settings.value("mainwindow/current_view", "My Calendar", type=str)
        if last_view not in self._views:
            last_view = "My Calendar"
        self.switch_view(last_view)

    def sidebar_width(self) -> int:
        sizes = self.splitter.sizes()
        return sizes[0] if sizes else 0
