"""SQLite cache layer bridging FRED client and local storage.

Per ADR-0002 Musts 7.2, 7.4, 7.7 and ADR-0005 storage design.

Public API:
    cache = Cache(fred_client)
    metadata = cache.get_metadata(conn, "CPIAUCSL")
    observations = cache.get_observations(conn, "CPIAUCSL")
    cache.refresh(conn, "CPIAUCSL")
    last = cache.get_last_synced(conn, "CPIAUCSL")

The caller owns the connection (from database.get_connection()) and
transaction boundaries. Cache uses parameterized queries only.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import UTC, datetime, timedelta

from econ_app.services.fred_client import FREDAPIError, FREDClient
from econ_app.services.models import Observation, SeriesMetadata

log = logging.getLogger(__name__)

# How stale metadata can be before we auto-refresh (only if observations request
# also triggers a fetch — we never fetch metadata alone unless forced).
METADATA_STALENESS = timedelta(hours=1)

SYNC_STATUS_SUCCESS = "success"
SYNC_STATUS_ERROR = "error"


class Cache:
    """Cache layer sitting between FRED API and SQLite storage."""

    def __init__(self, fred_client: FREDClient) -> None:
        self._client = fred_client

    # ---------------------------------------------------------------- reads

    def get_metadata(
        self,
        conn: sqlite3.Connection,
        series_id: str,
        force_refresh: bool = False,
    ) -> SeriesMetadata:
        """Return metadata for a series.

        Fetches from FRED and caches if not present, or if force_refresh=True.
        """
        if not force_refresh:
            cached = self._read_metadata(conn, series_id)
            if cached is not None:
                return cached

        # Cache miss or forced refresh — hit FRED
        metadata = self._client.get_series_metadata(series_id)
        self._write_metadata(conn, metadata)
        return metadata

    def get_observations(
        self,
        conn: sqlite3.Connection,
        series_id: str,
        force_refresh: bool = False,
    ) -> list[Observation]:
        """Return observations for a series.

        Fetches from FRED if the cache is empty or force_refresh=True.
        Ensures metadata is present too (fetches if needed).
        """
        if not force_refresh:
            obs = self._read_observations(conn, series_id)
            if obs:
                return obs

        return self.refresh(conn, series_id)

    def get_last_synced(
        self,
        conn: sqlite3.Connection,
        series_id: str,
    ) -> datetime | None:
        """Return the timestamp of the most recent successful sync, or None."""
        row = conn.execute(
            "SELECT synced_at FROM sync_log "
            "WHERE series_id = ? AND status = ? "
            "ORDER BY synced_at DESC LIMIT 1",
            (series_id, SYNC_STATUS_SUCCESS),
        ).fetchone()
        if row is None:
            return None
        return datetime.fromisoformat(row["synced_at"])

    # ---------------------------------------------------------------- writes

    def refresh(
        self,
        conn: sqlite3.Connection,
        series_id: str,
    ) -> list[Observation]:
        """Force a fresh fetch from FRED. Updates metadata, observations, sync_log.

        Returns the fresh observation list. Raises FREDAPIError on failure
        (after recording an error entry in sync_log).
        """
        try:
            # Metadata first — ensures FK reference exists before observations
            metadata = self._client.get_series_metadata(series_id)
            self._write_metadata(conn, metadata)

            # Then observations
            observations = self._client.get_observations(series_id)
            self._write_observations(conn, series_id, observations)

            # Success log entry
            self._log_sync(
                conn,
                series_id,
                observation_count=len(observations),
                status=SYNC_STATUS_SUCCESS,
                error_message=None,
            )
            conn.commit()
            log.info("Refreshed %s: %d observations", series_id, len(observations))
            return observations

        except FREDAPIError as e:
            # Log the failure — but roll back any partial writes
            conn.rollback()
            self._log_sync(
                conn,
                series_id,
                observation_count=None,
                status=SYNC_STATUS_ERROR,
                error_message=str(e),
            )
            conn.commit()
            raise

    # ---------------------------------------------------------------- internals

    @staticmethod
    def _read_metadata(conn: sqlite3.Connection, series_id: str) -> SeriesMetadata | None:
        row = conn.execute(
            "SELECT id, title, notes, frequency, frequency_short, units, units_short, "
            "       seasonal_adjustment, seasonal_adjustment_short, observation_start, "
            "       observation_end, last_updated_fred, popularity "
            "FROM series WHERE id = ?",
            (series_id,),
        ).fetchone()
        if row is None:
            return None
        from datetime import date

        return SeriesMetadata(
            id=row["id"],
            title=row["title"],
            notes=row["notes"],
            frequency=row["frequency"],
            frequency_short=row["frequency_short"] or "",
            units=row["units"],
            units_short=row["units_short"] or "",
            seasonal_adjustment=row["seasonal_adjustment"] or "",
            seasonal_adjustment_short=row["seasonal_adjustment_short"] or "",
            observation_start=date.fromisoformat(row["observation_start"]),
            observation_end=date.fromisoformat(row["observation_end"]),
            last_updated=datetime.fromisoformat(row["last_updated_fred"]),
            popularity=row["popularity"] or 0,
        )

    @staticmethod
    def _write_metadata(conn: sqlite3.Connection, metadata: SeriesMetadata) -> None:
        conn.execute(
            "INSERT OR REPLACE INTO series ("
            "  id, title, notes, frequency, frequency_short, units, units_short, "
            "  seasonal_adjustment, seasonal_adjustment_short, observation_start, "
            "  observation_end, last_updated_fred, popularity, fetched_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                metadata.id,
                metadata.title,
                metadata.notes,
                metadata.frequency,
                metadata.frequency_short,
                metadata.units,
                metadata.units_short,
                metadata.seasonal_adjustment,
                metadata.seasonal_adjustment_short,
                metadata.observation_start.isoformat(),
                metadata.observation_end.isoformat(),
                metadata.last_updated.isoformat(),
                metadata.popularity,
                datetime.now(UTC).isoformat(),
            ),
        )

    @staticmethod
    def _read_observations(conn: sqlite3.Connection, series_id: str) -> list[Observation]:
        from datetime import date

        rows = conn.execute(
            "SELECT date, value FROM observations WHERE series_id = ? ORDER BY date",
            (series_id,),
        ).fetchall()
        return [
            Observation(
                date=date.fromisoformat(r["date"]),
                value=r["value"],
                is_missing=(r["value"] is None),
            )
            for r in rows
        ]

    @staticmethod
    def _write_observations(
        conn: sqlite3.Connection,
        series_id: str,
        observations: list[Observation],
    ) -> None:
        # Executemany with parameterized query in a single transaction
        conn.executemany(
            "INSERT OR REPLACE INTO observations (series_id, date, value) VALUES (?, ?, ?)",
            [(series_id, obs.date.isoformat(), obs.value) for obs in observations],
        )

    @staticmethod
    def _log_sync(
        conn: sqlite3.Connection,
        series_id: str,
        observation_count: int | None,
        status: str,
        error_message: str | None,
    ) -> None:
        conn.execute(
            "INSERT INTO sync_log (series_id, synced_at, observation_count, status, error_message) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                series_id,
                datetime.now(UTC).isoformat(),
                observation_count,
                status,
                error_message,
            ),
        )
