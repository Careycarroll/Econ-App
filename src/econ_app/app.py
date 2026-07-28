"""QApplication entry point for Econ-App.

Post-Issue-#17, this module also provides the About dialog helper that the
menu bar's About action calls.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox, QWidget

from econ_app import __version__
from econ_app.ui.main_window import MainWindow


def main() -> int:
    """Create the QApplication, show the main window, run the event loop."""
    # Configure structured logging first so early failures land in the log file.
    from econ_app.services.logging_setup import configure_logging

    log_path = configure_logging()

    # Install crash handlers before creating QApplication so any startup
    # exceptions are captured with a traceback rather than lost to Qt.
    from econ_app.services.error_handling import install_handlers

    install_handlers()

    import logging

    logging.getLogger(__name__).info("Econ-App starting. Log file: %s", log_path)

    from econ_app.config import load_env
    from econ_app.services.database import ensure_ready

    # Load env before anything else so downstream code sees FRED_API_KEY
    load_env()

    # Ensure database is initialized
    ensure_ready()

    app = QApplication(sys.argv)
    app.setApplicationName("Econ-App")
    app.setApplicationDisplayName("Econ-App")
    app.setOrganizationName("Carey Carroll")

    window = MainWindow()
    window.show()

    return app.exec()


def show_about_dialog(parent: QWidget | None = None) -> None:
    """Display the About dialog. Called from the Econ-App menu."""
    QMessageBox.about(
        parent,
        "About Econ-App",
        (
            f"<h3>Econ-App</h3>"
            f"<p>Version {__version__}</p>"
            f"<p>A personal desktop application for exploring and learning "
            f"about U.S. economic data.</p>"
            f'<p>Data via <a href="https://fred.stlouisfed.org/">FRED</a> '
            f"(Federal Reserve Economic Data).</p>"
        ),
    )
