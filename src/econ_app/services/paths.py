"""Cross-platform data directory resolution.

Per ADR-0005, the real SQLite cache lives in the platform's standard
application data directory (macOS: ~/Library/Application Support/Econ-App/,
Linux: ~/.local/share/econ-app/, Windows: %APPDATA%/Econ-App/).

Test fixtures live in tests/fixtures/ in the repository.
"""

from __future__ import annotations

from pathlib import Path

from platformdirs import user_data_dir

APP_NAME = "Econ-App"
APP_AUTHOR = "Carey Carroll"


def get_data_dir() -> Path:
    """Return the platform-appropriate app data directory, creating it if needed."""
    d = Path(user_data_dir(APP_NAME, APP_AUTHOR))
    d.mkdir(parents=True, exist_ok=True)
    return d


def get_database_path() -> Path:
    """Return the path to the SQLite database file."""
    return get_data_dir() / "econ_app.sqlite"


def get_project_root() -> Path:
    """Return the repository root — used to locate schema.sql at runtime."""
    # This file lives at src/econ_app/services/paths.py, so project root is 3 levels up
    return Path(__file__).resolve().parents[3]


def get_schema_path() -> Path:
    """Return the path to schema.sql in the repository."""
    return get_project_root() / "schema.sql"
