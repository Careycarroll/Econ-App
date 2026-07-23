"""Tests for the Core Indicators view.

Uses in-memory SQLite seeded with a small fixture so the view can be exercised
without hitting the real database or the FRED API.
"""

from __future__ import annotations

import sqlite3
from unittest.mock import patch

import pytest

from econ_app.services.database import init_schema
from econ_app.services.series_catalog import DB_COLUMNS

SAMPLE_ROWS = [
    {
        "series_id": "CPIAUCSL",
        "title": "Consumer Price Index for All Urban Consumers",
        "app_core_status": "Core",
        "review_status": "accepted_core_seed",
        "seed_source": "curated_core_series",
        "suggested_series_core_status": "Core",
        "suggested_core_domain": "Inflation/Prices",
        "suggested_market_relevance": "High",
        "suggested_economist_relevance": "High",
        "candidate_core_score": 150,
        "candidate_core_reasons": "benchmark_core_series_id",
        "popularity": 97,
        "frequency": "Monthly",
        "units": "Index 1982-1984=100",
        "seasonal_adjustment": "Seasonally Adjusted",
        "observation_start": "1947-01-01",
        "observation_end": "2026-06-01",
        "last_updated_fred": "2026-07-14 08:10:40-05",
        "release_ids": "10",
        "release_names": "Consumer Price Index",
        "series_core_status": "Core",
        "market_relevance": "High",
        "economist_relevance": "High",
        "seeded_at": "2026-07-23T00:00:00+00:00",
    },
    {
        "series_id": "UNRATE",
        "title": "Unemployment Rate",
        "app_core_status": "Core",
        "review_status": "accepted_core_seed",
        "seed_source": "curated_core_series",
        "suggested_series_core_status": "Core",
        "suggested_core_domain": "Labor",
        "suggested_market_relevance": "High",
        "suggested_economist_relevance": "High",
        "candidate_core_score": 150,
        "candidate_core_reasons": "benchmark_core_series_id",
        "popularity": 97,
        "frequency": "Monthly",
        "units": "Percent",
        "seasonal_adjustment": "Seasonally Adjusted",
        "observation_start": "1948-01-01",
        "observation_end": "2026-06-01",
        "last_updated_fred": "2026-07-02 08:31:40-05",
        "release_ids": "50",
        "release_names": "Employment Situation",
        "series_core_status": "Core",
        "market_relevance": "High",
        "economist_relevance": "High",
        "seeded_at": "2026-07-23T00:00:00+00:00",
    },
    {
        "series_id": "DRCCLACBS",
        "title": "Delinquency Rate on Credit Card Loans, All Commercial Banks",
        "app_core_status": "Candidate-Core",
        "review_status": "needs_review",
        "seed_source": "core_watchlist_series",
        "suggested_series_core_status": "Candidate-Core",
        "suggested_core_domain": "Money/Credit/Banking",
        "suggested_market_relevance": "Medium",
        "suggested_economist_relevance": "High",
        "candidate_core_score": 90,
        "candidate_core_reasons": "popularity>=80",
        "popularity": 82,
        "frequency": "Quarterly, End of Period",
        "units": "Percent",
        "seasonal_adjustment": "Seasonally Adjusted",
        "observation_start": "1991-01-01",
        "observation_end": "2026-01-01",
        "last_updated_fred": "2026-05-19 08:08:24-05",
        "release_ids": "94",
        "release_names": "Charge-Off and Delinquency Rates",
        "series_core_status": None,
        "market_relevance": None,
        "economist_relevance": None,
        "seeded_at": "2026-07-23T00:00:00+00:00",
    },
]


@pytest.fixture()
def in_memory_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    init_schema(conn)

    placeholders = ", ".join("?" for _ in DB_COLUMNS)
    columns_sql = ", ".join(DB_COLUMNS)
    conn.executemany(
        f"INSERT INTO fred_core_series ({columns_sql}) VALUES ({placeholders})",
        [tuple(row[col] for col in DB_COLUMNS) for row in SAMPLE_ROWS],
    )
    conn.commit()
    yield conn
    conn.close()


def _install_fake_connection(monkeypatch, conn):
    """Route the view's get_connection() calls to our in-memory connection.

    Wraps in a shim so `with get_connection() as c:` works without closing
    the shared in-memory DB.
    """
    from econ_app.ui.views import core_indicators as view_module

    class _ConnShim:
        def __enter__(self):
            return conn

        def __exit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(view_module, "get_connection", lambda: _ConnShim())


def test_core_indicators_view_loads_rows(qtbot, monkeypatch, in_memory_conn) -> None:
    """View pulls seeded rows out of SQLite and renders them in the table."""
    _install_fake_connection(monkeypatch, in_memory_conn)

    from econ_app.ui.views.core_indicators import CoreIndicatorsView

    view = CoreIndicatorsView()
    qtbot.addWidget(view)
    view.ensure_loaded()

    assert view._loaded is True
    assert view.table.rowCount() == len(SAMPLE_ROWS)

    displayed_ids = {view.table.item(row, 0).text() for row in range(view.table.rowCount())}
    assert displayed_ids == {r["series_id"] for r in SAMPLE_ROWS}

    assert "Core" in view.summary_label.text()
    assert "Candidate-Core" in view.summary_label.text()


def test_core_indicators_search_filters_rows(qtbot, monkeypatch, in_memory_conn) -> None:
    """Typing in the search box hides non-matching rows."""
    _install_fake_connection(monkeypatch, in_memory_conn)

    from econ_app.ui.views.core_indicators import CoreIndicatorsView

    view = CoreIndicatorsView()
    qtbot.addWidget(view)
    view.ensure_loaded()

    view.search_box.setText("unemployment")

    visible_ids: list[str] = []
    for row in range(view.table.rowCount()):
        if not view.table.isRowHidden(row):
            visible_ids.append(view.table.item(row, 0).text())

    assert visible_ids == ["UNRATE"]


def test_core_indicators_open_selected_emits_signal(qtbot, monkeypatch, in_memory_conn) -> None:
    """Opening a selected series emits series_requested with its FRED ID."""
    _install_fake_connection(monkeypatch, in_memory_conn)

    from econ_app.ui.views.core_indicators import CoreIndicatorsView

    view = CoreIndicatorsView()
    qtbot.addWidget(view)
    view.ensure_loaded()

    # Find and select the UNRATE row.
    target_row = None
    for row in range(view.table.rowCount()):
        if view.table.item(row, 0).text() == "UNRATE":
            target_row = row
            break
    assert target_row is not None
    view.table.selectRow(target_row)

    assert view.open_button.isEnabled()

    with qtbot.waitSignal(view.series_requested, timeout=1000) as blocker:
        view._open_selected_series()

    assert blocker.args == ["UNRATE"]


def test_main_window_core_indicator_selection_loads_series(
    qtbot, monkeypatch, in_memory_conn
) -> None:
    """MainWindow routes series_requested to Series Detail's load_series."""
    _install_fake_connection(monkeypatch, in_memory_conn)

    from econ_app.ui.main_window import MainWindow

    with patch("econ_app.ui.views.series_detail.get_app_cache") as mock_get_app_cache:
        mock_get_app_cache.side_effect = RuntimeError(
            "No FRED API key configured; safe stub for test."
        )

        window = MainWindow()
        qtbot.addWidget(window)

        window.switch_view("Core Indicators")
        core_view = window._views["Core Indicators"]
        core_view.ensure_loaded()

        target_row = None
        for row in range(core_view.table.rowCount()):
            if core_view.table.item(row, 0).text() == "CPIAUCSL":
                target_row = row
                break
        assert target_row is not None
        core_view.table.selectRow(target_row)

        core_view._open_selected_series()

        # Should now be on Series Detail view.
        detail_view = window._views["Series Detail"]
        assert window.content_stack.currentWidget() is detail_view
        # And it should have attempted to load the requested series ID.
        assert detail_view._series_id == "CPIAUCSL"
