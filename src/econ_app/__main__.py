"""Entry point for `python -m econ_app`.

For Issue #12 (project scaffold), this just proves the package structure works.
The actual PySide6 window is added in Issue #14.
"""

from __future__ import annotations

import sys

from econ_app import __version__


def main() -> int:
    """Placeholder entry point.

    In Issue #14 this will instantiate QApplication and open the main window.
    For now it just confirms the package is installed and importable.
    """
    print(f"Econ-App v{__version__}")
    print("Scaffold OK — the PySide6 window arrives in Issue #14.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
