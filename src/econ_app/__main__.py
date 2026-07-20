"""Entry point for `python -m econ_app`.

Delegates to app.main() which creates the QApplication and opens the window.
"""

from __future__ import annotations

import sys

from econ_app.app import main

if __name__ == "__main__":
    sys.exit(main())
