"""Placeholder view classes for v0.1.

Real content lands in later milestones (v0.2 Calendar, v0.4 Series Detail,
v0.5 Explorer, v0.6 Core Indicators).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout

from econ_app.ui.views.base_view import BaseView


def _make_placeholder(text: str, subtext: str) -> QLabel:
    label = QLabel(f"<h2>{text}</h2><p style='color:#666;'>{subtext}</p>")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setTextFormat(Qt.TextFormat.RichText)
    return label


class CalendarView(BaseView):
    view_name = "Calendar"

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_make_placeholder("Calendar view", "Coming in v0.2 — Issue #20"))
        self.sidebar_widget = QLabel("Calendar filters\n(placeholder)")


class ExplorerView(BaseView):
    view_name = "Explorer"

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_make_placeholder("Explorer view", "Coming in v0.5"))
        self.sidebar_widget = QLabel("Explorer navigation\n(placeholder)")


class SeriesDetailView(BaseView):
    view_name = "Series Detail"

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_make_placeholder("Series Detail view", "Coming in v0.4"))
        self.sidebar_widget = QLabel("Series navigation\n(placeholder)")


class CoreIndicatorsView(BaseView):
    view_name = "Core Indicators"

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_make_placeholder("Core Indicators view", "Coming in v0.6"))
        self.sidebar_widget = QLabel("Market filters\n(placeholder)")
