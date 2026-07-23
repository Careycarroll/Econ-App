"""Tests for the committed FRED core series seed catalog import."""

from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

import pytest

from econ_app.services.database import init_schema
from econ_app.services.series_catalog import (
    REQUIRED_COLUMNS,
    get_core_series,
    list_core_series,
    seed_core_series,
)


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    init_schema(c)
    yield c
    c.close()


@pytest.fixture()
def seed_csv(tmp_path: Path) -> Path:
    path = tmp_path / "fred_core_series_seed.csv"
    rows = [
        {
            "series_id": "GDP",
            "title": "Gross Domestic Product",
            "app_core_status": "Core",
            "review_status": "accepted_core_seed",
            "seed_source": "curated_core_series",
            "suggested_series_core_status": "Core",
            "suggested_core_domain": "Growth/Output",
            "suggested_market_relevance": "High",
            "suggested_economist_relevance": "High",
            "candidate_core_score": "150",
            "candidate_core_reasons": "benchmark_core_series_id",
            "popularity": "91",
            "frequency": "Quarterly",
            "units": "Billions of Dollars",
            "seasonal_adjustment": "Seasonally Adjusted Annual Rate",
            "observation_start": "1947-01-01",
            "observation_end": "2026-01-01",
            "last_updated": "2026-06-25 07:50:52-05",
            "release_ids": "53",
            "release_names": "Gross Domestic Product",
            "series_core_status": "Core",
            "market_relevance": "High",
            "economist_relevance": "High",
        },
        {
            "series_id": "U6RATE",
            "title": "Total Unemployed Plus Marginally Attached and Part Time for Economic Reasons",
            "app_core_status": "Candidate-Core",
            "review_status": "needs_review",
            "seed_source": "core_watchlist_series",
            "suggested_series_core_status": "Candidate-Core",
            "suggested_core_domain": "Labor",
            "suggested_market_relevance": "Medium",
            "suggested_economist_relevance": "High",
            "candidate_core_score": "80",
            "candidate_core_reasons": "popularity>=60; macro_market_keyword",
            "popularity": "71",
            "frequency": "Monthly",
            "units": "Percent",
            "seasonal_adjustment": "Seasonally Adjusted",
            "observation_start": "1994-01-01",
            "observation_end": "2026-06-01",
            "last_updated": "2026-07-02 08:31:35-05",
            "release_ids": "50",
            "release_names": "Employment Situation",
            "series_core_status": "TBD",
            "market_relevance": "TBD",
            "economist_relevance": "TBD",
        },
    ]

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    return path


def test_seed_core_series_imports_rows(conn, seed_csv: Path) -> None:
    imported = seed_core_series(conn, seed_csv)

    assert imported == 2
    count = conn.execute("SELECT COUNT(*) AS n FROM fred_core_series").fetchone()["n"]
    assert count == 2


def test_seed_core_series_is_idempotent(conn, seed_csv: Path) -> None:
    seed_core_series(conn, seed_csv)
    seed_core_series(conn, seed_csv)

    count = conn.execute("SELECT COUNT(*) AS n FROM fred_core_series").fetchone()["n"]
    assert count == 2


def test_get_core_series_returns_one_row(conn, seed_csv: Path) -> None:
    seed_core_series(conn, seed_csv)

    row = get_core_series(conn, "GDP")

    assert row is not None
    assert row["title"] == "Gross Domestic Product"
    assert row["app_core_status"] == "Core"
    assert row["candidate_core_score"] == 150


def test_list_core_series_filters_by_status_and_domain(conn, seed_csv: Path) -> None:
    seed_core_series(conn, seed_csv)

    rows = list_core_series(conn, app_core_status="Candidate-Core", domain="Labor")

    assert [row["series_id"] for row in rows] == ["U6RATE"]


def test_missing_seed_file_returns_zero(conn, tmp_path: Path) -> None:
    missing = tmp_path / "missing.csv"

    imported = seed_core_series(conn, missing)

    assert imported == 0
