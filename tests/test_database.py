"""Tests for src/econ_app/services/database.py.

Uses an in-memory SQLite database so tests don't touch the real cache.
"""

from __future__ import annotations

import sqlite3

import pytest


@pytest.fixture()
def in_memory_conn():
    """Provide an in-memory SQLite connection with the schema applied."""
    from econ_app.services.database import init_schema

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)
    yield conn
    conn.close()


def test_schema_creates_expected_tables(in_memory_conn) -> None:
    """init_schema creates series, observations, sync_log tables."""
    rows = in_memory_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = {r["name"] for r in rows}
    assert {"series", "observations", "sync_log", "_schema_version"}.issubset(names)


def test_schema_version_recorded(in_memory_conn) -> None:
    """_schema_version table has exactly one row after init."""
    rows = in_memory_conn.execute("SELECT version FROM _schema_version").fetchall()
    assert len(rows) == 1
    assert rows[0]["version"] == 1


def test_init_schema_idempotent(in_memory_conn) -> None:
    """Running init_schema twice doesn't error or duplicate version rows."""
    from econ_app.services.database import init_schema

    init_schema(in_memory_conn)
    rows = in_memory_conn.execute("SELECT * FROM _schema_version").fetchall()
    assert len(rows) == 1


def test_foreign_key_cascade_on_delete(in_memory_conn) -> None:
    """Deleting a series cascades to its observations. sync_log is NOT cascaded (audit trail)."""
    from datetime import UTC, datetime

    now = datetime.now(UTC).isoformat()
    in_memory_conn.execute(
        "INSERT INTO series (id, title, frequency, units, fetched_at) VALUES (?, ?, ?, ?, ?)",
        ("TEST1", "Test Series", "Monthly", "Percent", now),
    )
    in_memory_conn.execute(
        "INSERT INTO observations (series_id, date, value) VALUES (?, ?, ?)",
        ("TEST1", "2024-01-01", 1.5),
    )
    in_memory_conn.execute(
        "INSERT INTO sync_log (series_id, synced_at, status) VALUES (?, ?, ?)",
        ("TEST1", now, "success"),
    )

    in_memory_conn.execute("DELETE FROM series WHERE id = ?", ("TEST1",))
    in_memory_conn.commit()

    obs_count = in_memory_conn.execute(
        "SELECT COUNT(*) as n FROM observations WHERE series_id = ?", ("TEST1",)
    ).fetchone()["n"]
    log_count = in_memory_conn.execute(
        "SELECT COUNT(*) as n FROM sync_log WHERE series_id = ?", ("TEST1",)
    ).fetchone()["n"]

    assert obs_count == 0, "observations should cascade"
    assert log_count == 1, "sync_log should persist (audit trail)"
