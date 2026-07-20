"""Base class for main-content views.

Each view exposes a `sidebar_widget` that MainWindow swaps into the sidebar
when the view becomes active.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QWidget


class BaseView(QWidget):
    """Base class for views. Subclasses set view_name and provide widgets."""

    view_name: str = ""

    def __init__(self) -> None:
        super().__init__()
        self.sidebar_widget: QWidget = QLabel(f"{self.view_name} sidebar (placeholder)")
