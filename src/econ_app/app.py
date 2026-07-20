"""QApplication + main window entry point for Econ-App.

Per Issue #14, this creates a blank native window. Menu bar (#17),
sidebar layout (#15), and content (subsequent issues) are added later.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMainWindow


class MainWindow(QMainWindow):
    """The application's main window.

    In v0.1 this is intentionally empty — just proves the shell renders.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Econ-App")
        self.resize(1400, 900)


def main() -> int:
    """Create the QApplication, show the main window, run the event loop."""
    app = QApplication(sys.argv)
    app.setApplicationName("Econ-App")
    app.setOrganizationName("Carey Carroll")

    window = MainWindow()
    window.show()

    return app.exec()
