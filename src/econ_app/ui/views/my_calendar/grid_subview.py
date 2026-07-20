"""Grid sub-view for My Calendar.

Monthly calendar grid (7 cols x 6 rows). Empty cells in v0.2; real release
data lands in v0.7.
"""

from __future__ import annotations

import calendar
from datetime import date

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class GridSubview(QWidget):
    """Grid sub-view — monthly calendar with release cells."""

    def __init__(self) -> None:
        super().__init__()
        self._current_date = date.today().replace(day=1)

        # Header row: prev, month/year label, next
        header_row = QHBoxLayout()
        header_row.setContentsMargins(16, 8, 16, 8)

        self._prev_button = QPushButton("<")
        self._next_button = QPushButton(">")
        self._prev_button.setFixedWidth(36)
        self._next_button.setFixedWidth(36)
        self._prev_button.clicked.connect(self._go_prev_month)
        self._next_button.clicked.connect(self._go_next_month)

        self._month_label = QLabel()
        self._month_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._month_label.setStyleSheet("font-size: 16px; font-weight: 600;")

        header_row.addWidget(self._prev_button)
        header_row.addWidget(self._month_label, stretch=1)
        header_row.addWidget(self._next_button)

        # Weekday header
        weekday_row = QGridLayout()
        weekday_row.setSpacing(0)
        for col, name in enumerate(["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]):
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet(
                "font-weight: 600; color: #666; padding: 6px; "
                "background-color: #f5f5f5; border-bottom: 1px solid #d0d0d0;"
            )
            weekday_row.addWidget(lbl, 0, col)
            weekday_row.setColumnStretch(col, 1)

        # Day grid (populated in _render_month)
        self._grid = QGridLayout()
        self._grid.setSpacing(0)
        self._grid_container = QWidget()
        self._grid_container.setLayout(self._grid)
        for col in range(7):
            self._grid.setColumnStretch(col, 1)

        # Assemble
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addLayout(header_row)
        layout.addLayout(weekday_row)
        layout.addWidget(self._grid_container, stretch=1)

        self._render_month()

    def _render_month(self) -> None:
        """Clear and repaint the grid for the current month."""
        # Clear existing cells
        while self._grid.count():
            item = self._grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        year = self._current_date.year
        month = self._current_date.month
        self._month_label.setText(f"{calendar.month_name[month]} {year}")

        # calendar.monthcalendar returns weeks with Monday-first; we want Sunday-first
        cal = calendar.Calendar(firstweekday=6)  # 6 = Sunday
        weeks = cal.monthdayscalendar(year, month)
        today = date.today()

        for row, week in enumerate(weeks):
            for col, day in enumerate(week):
                cell = self._make_cell(
                    day, year, month, is_today=(day != 0 and date(year, month, day) == today)
                )
                self._grid.addWidget(cell, row, col)
                self._grid.setRowStretch(row, 1)

    @staticmethod
    def _make_cell(day: int, year: int, month: int, is_today: bool) -> QFrame:
        """Build a single day cell. day=0 means empty (padding for month start/end)."""
        cell = QFrame()
        cell.setFrameShape(QFrame.Shape.StyledPanel)
        cell.setStyleSheet(
            "QFrame { background-color: white; border: 1px solid #e0e0e0; }"
            + ("QFrame { background-color: #fff8dc; }" if is_today else "")
        )
        cell.setMinimumHeight(80)

        layout = QVBoxLayout(cell)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(2)

        if day == 0:
            # Empty padding cell
            cell.setStyleSheet("QFrame { background-color: #fafafa; border: 1px solid #e0e0e0; }")
            return cell

        day_label = QLabel(str(day))
        day_label.setStyleSheet(
            "font-weight: 600; color: #333;" + (" color: #b8860b;" if is_today else "")
        )
        layout.addWidget(day_label)

        # Placeholder for future release entries
        layout.addStretch(1)

        return cell

    def _go_prev_month(self) -> None:
        year = self._current_date.year
        month = self._current_date.month - 1
        if month < 1:
            month = 12
            year -= 1
        self._current_date = date(year, month, 1)
        self._render_month()

    def _go_next_month(self) -> None:
        year = self._current_date.year
        month = self._current_date.month + 1
        if month > 12:
            month = 1
            year += 1
        self._current_date = date(year, month, 1)
        self._render_month()
