"""Application-scoped cache instance.

Views call get_app_cache() to get a Cache backed by the real FRED client
and a fresh SQLite connection per operation.

Reason for this indirection: the Cache class takes a connection per method
so it's testable with in-memory SQLite. In production, we always want a
fresh connection from get_connection(). This module abstracts that away.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from econ_app.config import get_fred_api_key
from econ_app.services.cache import Cache
from econ_app.services.database import get_connection
from econ_app.services.fred_client import FREDClient
from econ_app.services.models import Observation, SeriesMetadata

log = logging.getLogger(__name__)


class AppCache:
    """Convenience wrapper that owns its own FRED client and opens fresh connections."""

    def __init__(self) -> None:
        api_key = get_fred_api_key()
        if not api_key:
            raise RuntimeError("No FRED API key configured. Set FRED_API_KEY in .env.")
        self._client = FREDClient(api_key=api_key)
        self._cache = Cache(self._client)

    def get_metadata(self, series_id: str, force_refresh: bool = False) -> SeriesMetadata:
        conn = get_connection()
        try:
            return self._cache.get_metadata(conn, series_id, force_refresh=force_refresh)
        finally:
            conn.close()

    def get_observations(self, series_id: str, force_refresh: bool = False) -> list[Observation]:
        conn = get_connection()
        try:
            return self._cache.get_observations(conn, series_id, force_refresh=force_refresh)
        finally:
            conn.close()

    def refresh(self, series_id: str) -> list[Observation]:
        conn = get_connection()
        try:
            return self._cache.refresh(conn, series_id)
        finally:
            conn.close()

    def get_last_synced(self, series_id: str):
        conn = get_connection()
        try:
            return self._cache.get_last_synced(conn, series_id)
        finally:
            conn.close()

    def close(self) -> None:
        self._client.close()


@lru_cache(maxsize=1)
def get_app_cache() -> AppCache:
    """Return the app-wide AppCache singleton."""
    return AppCache()
