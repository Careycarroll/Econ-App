"""Core Indicators view.

Renders the committed FRED core-series seed catalog imported into SQLite.
Users can browse, search, and open any series in the Series Detail view.

Per v0.6 milestone (issue #52).
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from econ_app.services.database import get_connection
from econ_app.services.series_catalog import list_core_series
from econ_app.ui.views.base_view import BaseView

log = logging.getLogger(__name__)

TABLE_COLUMNS: list[tuple[str, str]] = [
    ("series_id", "Series ID"),
    ("title", "Title"),
    ("app_core_status", "Status"),
    ("suggested_core_domain", "Domain"),
    ("suggested_market_relevance", "Market"),
    ("suggested_economist_relevance", "Economist"),
    ("frequency", "Frequency"),
    ("units", "Units"),
    ("popularity", "Popularity"),
]

STATUS_SORT_ORDER = {"Core": 0, "Candidate-Core": 1}


def _row_value(row: Any, key: str) -> Any:
    """Read a value from a sqlite3.Row or any mapping-like object."""
    try:
        return row[key]
    except (KeyError, IndexError):
        return None


class CoreIndicatorsView(BaseView):
    """Browse the seeded Core and Candidate-Core FRED indicators."""

    view_name = "Core Indicators"

    # Emitted when the user opens a series. MainWindow connects this to
    # switch to Series Detail and load the requested series.
    series_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[Any] = []
        self._loaded = False

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QLabel("<h2>Core Indicators</h2>")
        header.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(header)

        description = QLabel(
            "Browse the app's seeded FRED Core and Candidate-Core indicators. "
            "Double-click a row, or select a row and click Open Series, to view its chart."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #555;")
        layout.addWidget(description)

        toolbar = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(
            "Search by series ID, title, domain, frequency, or units..."
        )
        self.search_box.textChanged.connect(self._apply_search_filter)
        toolbar.addWidget(self.search_box, stretch=1)

        self.open_button = QPushButton("Open Series")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self._open_selected_series)
        toolbar.addWidget(self.open_button)
        layout.addLayout(toolbar)

        self.summary_label = QLabel("Loading core indicators...")
        self.summary_label.setStyleSheet("color: #666;")
        layout.addWidget(self.summary_label)

        self.table = QTableWidget(0, len(TABLE_COLUMNS))
        self.table.setObjectName("coreIndicatorsTable")
        self.table.setHorizontalHeaderLabels([label for _key, label in TABLE_COLUMNS])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.itemDoubleClicked.connect(lambda _item: self._open_selected_series())
        layout.addWidget(self.table, stretch=1)

        self.sidebar_widget = self._build_sidebar_widget()

    # ---------------------------------------------------------------- lifecycle

    def ensure_loaded(self) -> None:
        """Lazy-load catalog rows on first activation of the view."""
        if self._loaded:
            return
        self.reload()

    def reload(self) -> None:
        """Reload rows from the local SQLite catalog."""
        try:
            with get_connection() as conn:
                self._rows = list_core_series(conn, limit=1000)
        except Exception as exc:  # pragma: no cover - defensive UI boundary
            log.exception("Failed to load core indicators")
            self._rows = []
            self.summary_label.setText(f"Could not load core indicators: {exc}")
            self.table.setRowCount(0)
            self._loaded = False
            return

        self._loaded = True
        self._populate_table(self._rows)
        self._update_summary(self._rows)
        self._update_sidebar_summary(self._rows)

    # ---------------------------------------------------------------- sidebar

    def _build_sidebar_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        title = QLabel("<b>Core Indicators</b>")
        title.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(title)

        self.sidebar_summary_label = QLabel("Catalog not loaded")
        self.sidebar_summary_label.setWordWrap(True)
        layout.addWidget(self.sidebar_summary_label)

        hint = QLabel(
            "Filter chips arrive in issue #53. For now, use the search box in the main view."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)

        layout.addStretch(1)
        return widget

    def _update_sidebar_summary(self, rows: list[Any]) -> None:
        if not rows:
            self.sidebar_summary_label.setText("No indicators loaded.")
            return
        domain_counts: dict[str, int] = {}
        for row in rows:
            domain = str(_row_value(row, "suggested_core_domain") or "Other/Unclassified")
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        top_domains = sorted(domain_counts.items(), key=lambda item: (-item[1], item[0]))[:6]
        lines: list[str] = [f"Loaded {len(rows):,} seeded indicators.", ""]
        for domain, count in top_domains:
            lines.append(f"\u2022 {domain}: {count}")
        self.sidebar_summary_label.setText("\n".join(lines))

    # ---------------------------------------------------------------- table

    def _populate_table(self, rows: list[Any]) -> None:
        sorted_rows = sorted(
            rows,
            key=lambda r: (
                STATUS_SORT_ORDER.get(str(_row_value(r, "app_core_status") or ""), 99),
                -int(_row_value(r, "candidate_core_score") or 0),
                -int(_row_value(r, "popularity") or 0),
                str(_row_value(r, "series_id") or ""),
            ),
        )

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(sorted_rows))

        for row_index, row in enumerate(sorted_rows):
            for col_index, (key, _label) in enumerate(TABLE_COLUMNS):
                value = _row_value(row, key)
                display = "" if value is None else str(value)
                item = QTableWidgetItem(display)
                item.setData(Qt.ItemDataRole.UserRole, _row_value(row, "series_id"))
                if key == "popularity" and value is not None:
                    with contextlib.suppress(TypeError, ValueError):
                        item.setData(Qt.ItemDataRole.EditRole, int(value))
                self.table.setItem(row_index, col_index, item)

        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)
        self._apply_search_filter(self.search_box.text())

    def _update_summary(self, rows: list[Any]) -> None:
        total = len(rows)
        core = sum(1 for r in rows if _row_value(r, "app_core_status") == "Core")
        candidate = sum(1 for r in rows if _row_value(r, "app_core_status") == "Candidate-Core")
        domains = {str(_row_value(r, "suggested_core_domain")) for r in rows}
        self.summary_label.setText(
            f"{total:,} indicators loaded \u2014 "
            f"{core:,} Core, {candidate:,} Candidate-Core, {len(domains):,} domains."
        )

    # ---------------------------------------------------------------- search

    def _apply_search_filter(self, query: str) -> None:
        needle = (query or "").strip().lower()
        for row_index in range(self.table.rowCount()):
            if not needle:
                self.table.setRowHidden(row_index, False)
                continue
            visible = False
            for col_index in range(self.table.columnCount()):
                item = self.table.item(row_index, col_index)
                if item is not None and needle in item.text().lower():
                    visible = True
                    break
            self.table.setRowHidden(row_index, not visible)

    # ---------------------------------------------------------------- selection

    def _on_selection_changed(self) -> None:
        self.open_button.setEnabled(self._selected_series_id() is not None)

    def _selected_series_id(self) -> str | None:
        for item in self.table.selectedItems():
            data = item.data(Qt.ItemDataRole.UserRole)
            if data:
                return str(data)
        return None

    def _open_selected_series(self) -> None:
        series_id = self._selected_series_id()
        if series_id:
            log.info("Core Indicators: opening series %s", series_id)
            self.series_requested.emit(series_id)
