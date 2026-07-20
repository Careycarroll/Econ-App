"""Main window for Econ-App.

Per Issue #15, the central widget is a QSplitter with a sidebar
(280px default, 200-400px range) and a content area. Both panes have
subtle borders during development.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import QFrame, QMainWindow, QSplitter, QWidget

SIDEBAR_MIN_WIDTH = 200
SIDEBAR_MAX_WIDTH = 400
SIDEBAR_DEFAULT_WIDTH = 280
WINDOW_DEFAULT_WIDTH = 1400
WINDOW_DEFAULT_HEIGHT = 900


class MainWindow(QMainWindow):
    """The application's main window.

    Layout: horizontal QSplitter with sidebar (left) and content area (right).
    Sidebar width persists across sessions via QSettings.
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

        self._restore_sidebar_width()
        self.splitter.splitterMoved.connect(self._on_splitter_moved)

    def _build_sidebar(self) -> QWidget:
        """Sidebar pane. Contents are contextual per view — empty for now."""
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setMinimumWidth(SIDEBAR_MIN_WIDTH)
        sidebar.setMaximumWidth(SIDEBAR_MAX_WIDTH)
        # Development border — remove before v1
        sidebar.setStyleSheet(
            "#sidebar { background-color: #f0f0f0; border-right: 1px solid #d0d0d0; }"
        )
        return sidebar

    def _build_content_area(self) -> QWidget:
        """Content area. Views live here — empty for now."""
        content = QFrame()
        content.setObjectName("content")
        # Development border — remove before v1
        content.setStyleSheet("#content { background-color: #ffffff; }")
        return content

    def _restore_sidebar_width(self) -> None:
        """Restore sidebar width from QSettings, clamped to allowed range."""
        saved = self._settings.value("mainwindow/sidebar_width", SIDEBAR_DEFAULT_WIDTH, type=int)
        width = max(SIDEBAR_MIN_WIDTH, min(SIDEBAR_MAX_WIDTH, saved))
        self.splitter.setSizes([width, WINDOW_DEFAULT_WIDTH - width])

    def _on_splitter_moved(self, _pos: int, _index: int) -> None:
        """Persist sidebar width when the divider is dragged."""
        sizes = self.splitter.sizes()
        if sizes:
            self._settings.setValue("mainwindow/sidebar_width", sizes[0])

    def sidebar_width(self) -> int:
        """Return current sidebar width (used by tests)."""
        return self.splitter.sizes()[0]
