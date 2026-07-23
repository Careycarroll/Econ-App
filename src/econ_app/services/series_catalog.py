"""Import and query the committed FRED core series seed catalog.

The committed seed lives at:

    seeds/fred_core_series_seed.csv

It is intentionally small and app-facing. The large raw FRED metadata dump remains
local-only and ignored by Git.
"""

from __future__ import annotations

import csv
import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from econ_app.services.paths import get_project_root

log = logging.getLogger(__name__)

SEED_RELATIVE_PATH = Path("seeds") / "fred_core_series_seed.csv"

REQUIRED_COLUMNS = (
    "series_id",
    "title",
    "app_core_status",
    "review_status",
    "seed_source",
    "suggested_series_core_status",
    "suggested_core_domain",
    "suggested_market_relevance",
    "suggested_economist_relevance",
    "candidate_core_score",
    "candidate_core_reasons",
    "popularity",
    "frequency",
    "units",
    "seasonal_adjustment",
    "observation_start",
    "observation_end",
    "last_updated",
    "release_ids",
    "release_names",
    "series_core_status",
    "market_relevance",
    "economist_relevance",
)

DB_COLUMNS = (
    "series_id",
    "title",
    "app_core_status",
    "review_status",
    "seed_source",
    "suggested_series_core_status",
    "suggested_core_domain",
    "suggested_market_relevance",
    "suggested_economist_relevance",
    "candidate_core_score",
    "candidate_core_reasons",
    "popularity",
    "frequency",
    "units",
    "seasonal_adjustment",
    "observation_start",
    "observation_end",
    "last_updated_fred",
    "release_ids",
    "release_names",
    "series_core_status",
    "market_relevance",
    "economist_relevance",
    "seeded_at",
)


def get_default_seed_path() -> Path:
    """Return the committed FRED core series seed CSV path."""
    return get_project_root() / SEED_RELATIVE_PATH


def seed_core_series(conn: sqlite3.Connection, seed_path: Path | None = None) -> int:
    """Import the committed FRED core series seed into SQLite.

    The import is idempotent. Existing rows are replaced by series_id so the
    committed CSV remains the source of truth for the seed catalog.

    Args:
        conn: Open SQLite connection with schema initialized.
        seed_path: Optional override, mainly for tests.

    Returns:
        Number of rows imported. Returns 0 if the seed file is missing.
    """
    path = seed_path or get_default_seed_path()
    if not path.is_file():
        log.warning("FRED core series seed file not found: %s", path)
        return 0

    rows = _read_seed_rows(path)
    if not rows:
        return 0

    seeded_at = datetime.now(UTC).isoformat()
    placeholders = ", ".join("?" for _ in DB_COLUMNS)
    columns_sql = ", ".join(DB_COLUMNS)

    conn.executemany(
        f"INSERT OR REPLACE INTO fred_core_series ({columns_sql}) VALUES ({placeholders})",
        [_row_values(row, seeded_at) for row in rows],
    )
    log.info("Imported %d FRED core seed series from %s", len(rows), path)
    return len(rows)


def get_core_series(conn: sqlite3.Connection, series_id: str) -> sqlite3.Row | None:
    """Return one seeded core-series catalog row by FRED series ID."""
    return conn.execute(
        "SELECT * FROM fred_core_series WHERE series_id = ?",
        (series_id,),
    ).fetchone()


def list_core_series(
    conn: sqlite3.Connection,
    *,
    app_core_status: str | None = None,
    domain: str | None = None,
    limit: int = 500,
) -> list[sqlite3.Row]:
    """List seeded FRED series, optionally filtered by status and domain."""
    clauses: list[str] = []
    params: list[object] = []

    if app_core_status:
        clauses.append("app_core_status = ?")
        params.append(app_core_status)

    if domain:
        clauses.append("suggested_core_domain = ?")
        params.append(domain)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    safe_limit = max(1, min(limit, 5_000))
    params.append(safe_limit)

    return conn.execute(
        f"""
        SELECT *
        FROM fred_core_series
        {where_sql}
        ORDER BY
            CASE app_core_status WHEN 'Core' THEN 0 ELSE 1 END,
            candidate_core_score DESC,
            popularity DESC,
            series_id ASC
        LIMIT ?
        """,
        params,
    ).fetchall()


def _read_seed_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        missing = sorted(set(REQUIRED_COLUMNS) - set(reader.fieldnames or []))
        if missing:
            raise ValueError(f"FRED seed file is missing required columns: {missing}")
        return [dict(row) for row in reader]


def _row_values(row: dict[str, str], seeded_at: str) -> tuple[object, ...]:
    return (
        _clean(row["series_id"]),
        _clean(row["title"]),
        _clean(row["app_core_status"]),
        _clean(row["review_status"]),
        _clean(row["seed_source"]),
        _clean(row["suggested_series_core_status"]),
        _clean(row["suggested_core_domain"]),
        _clean(row["suggested_market_relevance"]),
        _clean(row["suggested_economist_relevance"]),
        _to_int(row["candidate_core_score"]),
        _clean(row["candidate_core_reasons"]),
        _to_int(row["popularity"]),
        _clean(row["frequency"]),
        _clean(row["units"]),
        _clean(row["seasonal_adjustment"]),
        _clean(row["observation_start"]),
        _clean(row["observation_end"]),
        _clean(row["last_updated"]),
        _clean(row["release_ids"]),
        _clean(row["release_names"]),
        _clean(row["series_core_status"]),
        _clean(row["market_relevance"]),
        _clean(row["economist_relevance"]),
        seeded_at,
    )


def _clean(value: object) -> str | None:
    text = "" if value is None else str(value).strip()
    return text or None


def _to_int(value: object) -> int | None:
    text = "" if value is None else str(value).strip()
    if not text:
        return None
    return int(float(text))
