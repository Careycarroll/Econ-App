"""List sub-view for My Calendar.

Shows upcoming releases in a scrollable list. Empty in v0.2; real data lands in v0.7.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ListSubview(QWidget):
    """List sub-view — shows FRED releases in a table/list format."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 8, 16, 16)

        # Empty state
        empty = QLabel(
            "<div style='color:#888; padding:60px 40px; text-align:center;'>"
            "<h3 style='color:#555;'>No releases to show yet</h3>"
            "<p>Your personal release calendar populates once the FRED client (v0.3) "
            "and catalog (v0.6) are in place.</p>"
            "<p>Come back in a few milestones.</p>"
            "</div>"
        )
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.setTextFormat(Qt.TextFormat.RichText)
        empty.setWordWrap(True)

        layout.addWidget(empty)
        layout.addStretch(1)
