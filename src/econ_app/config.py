"""Configuration loading for Econ-App.

- Reads .env from the project root (dev) or platform data dir (packaged)
- Provides get_fred_api_key() with format validation
- Non-fatal on missing/invalid: app can still launch to browse the shell,
  data-dependent views will show error states when FRED calls fail

Per ADR-0002 Must 8.1: FRED API key management via .env.
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path

from dotenv import load_dotenv

from econ_app.services.paths import get_data_dir, get_project_root

log = logging.getLogger(__name__)

FRED_KEY_PATTERN = re.compile(r"^[a-f0-9]{32}$")


def load_env() -> None:
    """Load environment variables from .env file.

    Search order:
    1. Project root (development)
    2. Platform data directory (packaged app)

    Silently no-ops if no .env is found; individual getters will handle missing values.
    """
    for candidate in (get_project_root() / ".env", get_data_dir() / ".env"):
        if candidate.is_file():
            load_dotenv(candidate)
            log.debug("Loaded environment from %s", candidate)
            return
    log.debug("No .env file found in project root or data directory")


def get_fred_api_key() -> str | None:
    """Return the FRED API key from environment, or None if missing/malformed.

    Logs a warning on malformed keys. Callers should handle None gracefully.
    """
    raw = os.environ.get("FRED_API_KEY", "").strip()
    if not raw:
        return None
    if not FRED_KEY_PATTERN.match(raw):
        log.warning(
            "FRED_API_KEY does not match expected format (32 hexadecimal chars). "
            "Data operations will fail until this is fixed."
        )
        return None
    return raw


def data_dir_path() -> Path:
    """Convenience re-export of the platform data directory (for logs/menus)."""
    return get_data_dir()
