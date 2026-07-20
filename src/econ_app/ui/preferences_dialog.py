"""Preferences dialog for Econ-App.

Per Issue #19, this is a modal dialog with three empty tabs.
Real preference controls arrive in later issues (font size in #65, etc.).
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)


class PreferencesDialog(QDialog):
    """Modal preferences dialog with 3 empty tabs (General / Appearance / Advanced)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Preferences")
        self.setModal(True)
        self.resize(600, 400)

        tabs = QTabWidget()
        tabs.addTab(self._empty_tab("General preferences — coming later"), "General")
        tabs.addTab(self._empty_tab("Appearance preferences — coming in Issue #65"), "Appearance")
        tabs.addTab(self._empty_tab("Advanced preferences — coming later"), "Advanced")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addWidget(buttons)

    @staticmethod
    def _empty_tab(text: str) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        label = QLabel(text)
        label.setStyleSheet("color: #888; padding: 40px;")
        layout.addWidget(label)
        layout.addStretch(1)
        return w
