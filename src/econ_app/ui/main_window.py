"""Main window for Econ-App.

Per Issue #15, the central widget is a QSplitter with a sidebar
(280px default, 200-400px range) and a content area.

Per Issue #16, the sidebar is toggleable via a button (top-left of the
main window) and the Cmd+\\ keyboard shortcut. Open/closed state and
width persist across sessions via QSettings.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QMainWindow,
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


class MainWindow(QMainWindow):
    """The application's main window.

    Layout: horizontal QSplitter with sidebar (left) and content area (right).
    Toggle button (top-left, floating) and Cmd+\\ shortcut hide/show the sidebar.
    Sidebar width and open/closed state persist across sessions via QSettings.
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

        # Content area takes all remaining space when window resizes
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        self.setCentralWidget(self.splitter)

        # Floating toggle button parented to the main window (not the sidebar),
        # so it remains visible when the sidebar is hidden.
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

        # Keyboard shortcut: Ctrl+\\ auto-maps to Cmd+\\ on macOS
        self._toggle_shortcut = QShortcut(QKeySequence("Ctrl+\\"), self)
        self._toggle_shortcut.activated.connect(self.toggle_sidebar)

        self._restore_state()
        self.splitter.splitterMoved.connect(self._on_splitter_moved)

    def _build_sidebar(self) -> QWidget:
        """Sidebar pane. Contents are contextual per view — empty for now."""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(SIDEBAR_MIN_WIDTH)
        sidebar.setMaximumWidth(SIDEBAR_MAX_WIDTH)
        sidebar.setStyleSheet(
            "#sidebar { background-color: #f0f0f0; border-right: 1px solid #d0d0d0; }"
        )
        return sidebar

    def _build_content_area(self) -> QWidget:
        """Content area. Views live here — empty for now."""
        content = QFrame()
        content.setObjectName("content")
        content.setStyleSheet("#content { background-color: #ffffff; }")
        return content

    def toggle_sidebar(self) -> None:
        """Show or hide the sidebar; persist the new state."""
        if not self.sidebar.isHidden():
            # Remember the current width before hiding
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
        """Restore sidebar width and open/closed state from QSettings."""
        saved_width = self._settings.value(
            "mainwindow/sidebar_width", SIDEBAR_DEFAULT_WIDTH, type=int
        )
        width = max(SIDEBAR_MIN_WIDTH, min(SIDEBAR_MAX_WIDTH, saved_width))
        self.splitter.setSizes([width, WINDOW_DEFAULT_WIDTH - width])

        is_open = self._settings.value("mainwindow/sidebar_open", True, type=bool)
        self.sidebar.setVisible(is_open)

    def _on_splitter_moved(self, _pos: int, _index: int) -> None:
        """Persist sidebar width when the divider is dragged."""
        sizes = self.splitter.sizes()
        if sizes and sizes[0] > 0:
            self._settings.setValue("mainwindow/sidebar_width", sizes[0])

    def sidebar_width(self) -> int:
        """Return current sidebar width (used by tests)."""
        return self.splitter.sizes()[0]
