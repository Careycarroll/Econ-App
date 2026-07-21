"""Tests for the cache layer.

Uses in-memory SQLite + a mocked FREDClient so tests are fast and deterministic.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime
from unittest.mock import MagicMock

import pytest

from econ_app.services.cache import Cache
from econ_app.services.database import init_schema
from econ_app.services.fred_client import FREDNotFoundError
from econ_app.services.models import Observation, SeriesMetadata


@pytest.fixture()
def conn():
    """In-memory SQLite with the schema applied."""
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    init_schema(c)
    yield c
    c.close()


@pytest.fixture()
def sample_metadata() -> SeriesMetadata:
    return SeriesMetadata(
        id="TEST1",
        title="Test Series",
        notes="A test series",
        frequency="Monthly",
        frequency_short="M",
        units="Index",
        units_short="Idx",
        seasonal_adjustment="Seasonally Adjusted",
        seasonal_adjustment_short="SA",
        observation_start=date(2020, 1, 1),
        observation_end=date(2024, 5, 1),
        last_updated=datetime(2024, 6, 12, 7, 41, 3, tzinfo=UTC),
        popularity=50,
    )


@pytest.fixture()
def sample_observations() -> list[Observation]:
    return [
        Observation(date=date(2024, 1, 1), value=100.0, is_missing=False),
        Observation(date=date(2024, 2, 1), value=101.5, is_missing=False),
        Observation(date=date(2024, 3, 1), value=None, is_missing=True),
    ]


# --------------------------------------------------------------- read behavior


def test_get_metadata_cache_miss_fetches_from_fred(conn, sample_metadata: SeriesMetadata) -> None:
    """First call to get_metadata fetches from FRED and caches."""
    mock_client = MagicMock()
    mock_client.get_series_metadata.return_value = sample_metadata

    cache = Cache(mock_client)
    result = cache.get_metadata(conn, "TEST1")

    assert result.id == "TEST1"
    mock_client.get_series_metadata.assert_called_once_with("TEST1")


def test_get_metadata_cache_hit_no_fetch(conn, sample_metadata: SeriesMetadata) -> None:
    """Second call to get_metadata reads from cache, no FRED call."""
    mock_client = MagicMock()
    mock_client.get_series_metadata.return_value = sample_metadata

    cache = Cache(mock_client)
    cache.get_metadata(conn, "TEST1")  # populates cache
    mock_client.reset_mock()

    result = cache.get_metadata(conn, "TEST1")
    assert result.id == "TEST1"
    mock_client.get_series_metadata.assert_not_called()


def test_get_metadata_force_refresh_refetches(conn, sample_metadata: SeriesMetadata) -> None:
    """force_refresh=True bypasses the cache."""
    mock_client = MagicMock()
    mock_client.get_series_metadata.return_value = sample_metadata

    cache = Cache(mock_client)
    cache.get_metadata(conn, "TEST1")
    mock_client.reset_mock()

    cache.get_metadata(conn, "TEST1", force_refresh=True)
    mock_client.get_series_metadata.assert_called_once()


def test_get_observations_cache_miss_triggers_refresh(
    conn,
    sample_metadata: SeriesMetadata,
    sample_observations: list[Observation],
) -> None:
    """First call to get_observations fetches metadata + observations."""
    mock_client = MagicMock()
    mock_client.get_series_metadata.return_value = sample_metadata
    mock_client.get_observations.return_value = sample_observations

    cache = Cache(mock_client)
    result = cache.get_observations(conn, "TEST1")

    assert len(result) == 3
    assert result[0].value == 100.0
    assert result[2].is_missing is True


def test_get_observations_cache_hit_no_fetch(
    conn,
    sample_metadata: SeriesMetadata,
    sample_observations: list[Observation],
) -> None:
    """Second call to get_observations reads from cache."""
    mock_client = MagicMock()
    mock_client.get_series_metadata.return_value = sample_metadata
    mock_client.get_observations.return_value = sample_observations

    cache = Cache(mock_client)
    cache.get_observations(conn, "TEST1")
    mock_client.reset_mock()

    result = cache.get_observations(conn, "TEST1")
    assert len(result) == 3
    mock_client.get_observations.assert_not_called()


def test_missing_values_stored_as_null(
    conn,
    sample_metadata: SeriesMetadata,
    sample_observations: list[Observation],
) -> None:
    """Observations with is_missing=True are stored as SQL NULL."""
    mock_client = MagicMock()
    mock_client.get_series_metadata.return_value = sample_metadata
    mock_client.get_observations.return_value = sample_observations

    cache = Cache(mock_client)
    cache.get_observations(conn, "TEST1")

    row = conn.execute(
        "SELECT value FROM observations WHERE series_id = 'TEST1' AND date = '2024-03-01'"
    ).fetchone()
    assert row["value"] is None


# --------------------------------------------------------------- refresh flow


def test_refresh_writes_sync_log_on_success(
    conn,
    sample_metadata: SeriesMetadata,
    sample_observations: list[Observation],
) -> None:
    """Successful refresh appends a success entry to sync_log."""
    mock_client = MagicMock()
    mock_client.get_series_metadata.return_value = sample_metadata
    mock_client.get_observations.return_value = sample_observations

    cache = Cache(mock_client)
    cache.refresh(conn, "TEST1")

    row = conn.execute(
        "SELECT status, observation_count FROM sync_log WHERE series_id = 'TEST1'"
    ).fetchone()
    assert row["status"] == "success"
    assert row["observation_count"] == 3


def test_refresh_writes_error_to_sync_log_on_failure(conn) -> None:
    """Failed refresh appends an error entry, no data written to observations."""
    mock_client = MagicMock()
    mock_client.get_series_metadata.side_effect = FREDNotFoundError("Series not found")

    cache = Cache(mock_client)
    with pytest.raises(FREDNotFoundError):
        cache.refresh(conn, "NOPE")

    row = conn.execute(
        "SELECT status, error_message FROM sync_log WHERE series_id = 'NOPE'"
    ).fetchone()
    assert row["status"] == "error"
    assert "not found" in row["error_message"].lower()

    obs_count = conn.execute(
        "SELECT COUNT(*) as n FROM observations WHERE series_id = 'NOPE'"
    ).fetchone()["n"]
    assert obs_count == 0


# --------------------------------------------------------------- sync log queries


def test_get_last_synced_returns_none_if_never_synced(conn) -> None:
    """No sync_log entries -> None."""
    cache = Cache(MagicMock())
    assert cache.get_last_synced(conn, "NEVER") is None


def test_get_last_synced_returns_most_recent_success(
    conn,
    sample_metadata: SeriesMetadata,
    sample_observations: list[Observation],
) -> None:
    """Returns the most recent success timestamp."""
    mock_client = MagicMock()
    mock_client.get_series_metadata.return_value = sample_metadata
    mock_client.get_observations.return_value = sample_observations

    cache = Cache(mock_client)
    cache.refresh(conn, "TEST1")

    result = cache.get_last_synced(conn, "TEST1")
    assert result is not None
    assert isinstance(result, datetime)


def test_get_last_synced_ignores_errors(conn) -> None:
    """Only successful syncs count."""
    mock_client = MagicMock()
    mock_client.get_series_metadata.side_effect = FREDNotFoundError("Not found")

    cache = Cache(mock_client)
    with pytest.raises(FREDNotFoundError):
        cache.refresh(conn, "TEST1")

    # An error sync happened but no success — should return None
    assert cache.get_last_synced(conn, "TEST1") is None
