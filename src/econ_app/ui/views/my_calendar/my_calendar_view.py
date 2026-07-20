"""My Calendar view — container with List/Grid sub-view toggle."""

from __future__ import annotations

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
)

from econ_app.ui.views.base_view import BaseView
from econ_app.ui.views.my_calendar.grid_subview import GridSubview
from econ_app.ui.views.my_calendar.list_subview import ListSubview

SUBVIEW_LIST = "list"
SUBVIEW_GRID = "grid"


class MyCalendarView(BaseView):
    """Personal FRED-backed calendar.

    Contains a segmented control at top switching between List and Grid sub-views.
    Both sub-views show empty states in v0.2; real data lands in v0.7.
    """

    view_name = "My Calendar"

    def __init__(self) -> None:
        super().__init__()

        self._settings = QSettings()

        # Sub-view stack
        self._list_view = ListSubview()
        self._grid_view = GridSubview()

        self._stack = QStackedWidget()
        self._stack.addWidget(self._list_view)
        self._stack.addWidget(self._grid_view)

        # Sub-view toggle (segmented control)
        toggle_row = QHBoxLayout()
        toggle_row.setContentsMargins(16, 12, 16, 8)
        toggle_row.setSpacing(0)

        self._list_button = QPushButton("List")
        self._grid_button = QPushButton("Grid")
        for btn in (self._list_button, self._grid_button):
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setStyleSheet(
                "QPushButton { padding: 4px 16px; border: 1px solid #c0c0c0; }"
                "QPushButton:checked { background-color: #e0e0e0; font-weight: 600; }"
            )

        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._button_group.addButton(self._list_button, 0)
        self._button_group.addButton(self._grid_button, 1)
        self._list_button.clicked.connect(lambda: self.set_subview(SUBVIEW_LIST))
        self._grid_button.clicked.connect(lambda: self.set_subview(SUBVIEW_GRID))

        toggle_row.addWidget(self._list_button)
        toggle_row.addWidget(self._grid_button)
        toggle_row.addStretch(1)

        # Overall layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(toggle_row)
        layout.addWidget(self._stack)

        # Sidebar placeholder
        self.sidebar_widget = QLabel(
            "My Calendar filters\n\nCategory, importance, and source filters\ncoming in v0.7."
        )
        self.sidebar_widget.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.sidebar_widget.setStyleSheet("color: #666; padding: 8px;")

        # Restore last sub-view
        saved = self._settings.value("mycalendar/subview", SUBVIEW_LIST, type=str)
        self.set_subview(saved if saved in (SUBVIEW_LIST, SUBVIEW_GRID) else SUBVIEW_LIST)

    def set_subview(self, name: str) -> None:
        """Switch between List and Grid sub-views. Persists selection."""
        if name == SUBVIEW_LIST:
            self._stack.setCurrentWidget(self._list_view)
            self._list_button.setChecked(True)
        elif name == SUBVIEW_GRID:
            self._stack.setCurrentWidget(self._grid_view)
            self._grid_button.setChecked(True)
        else:
            return
        self._settings.setValue("mycalendar/subview", name)

    @property
    def current_subview(self) -> str:
        """Return the currently-active sub-view name."""
        return SUBVIEW_LIST if self._stack.currentWidget() is self._list_view else SUBVIEW_GRID
