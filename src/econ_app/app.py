"""QApplication entry point for Econ-App.

Post-Issue-#15, MainWindow lives in econ_app.ui.main_window. This module
is just the QApplication wiring.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from econ_app.ui.main_window import MainWindow


def main() -> int:
    """Create the QApplication, show the main window, run the event loop."""
    app = QApplication(sys.argv)
    app.setApplicationName("Econ-App")
    app.setOrganizationName("Carey Carroll")

    window = MainWindow()
    window.show()

    return app.exec()
