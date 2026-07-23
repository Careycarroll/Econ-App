"""Core Indicators view.

Renders the committed FRED core-series seed catalog imported into SQLite.
Users can browse, search, filter by facet chips, and open any series in the
Series Detail view.

Per v0.6 milestones: issue #52 (rendering) and issue #53 (filter chips).
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import Iterable
from typing import Any

from PySide6.QtCore import QSettings, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
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

# Facet groups drive the sidebar chips.
# key: catalog column name
# label: sidebar section header
# settings_key: QSettings sub-key for persistence
FACETS: list[tuple[str, str, str]] = [
    ("app_core_status", "Core Status", "core_status"),
    ("suggested_core_domain", "Domain", "domain"),
    ("suggested_market_relevance", "Market Relevance", "market_relevance"),
    ("suggested_economist_relevance", "Economist Relevance", "economist_relevance"),
]

# Preferred display order for known values in specific facets.
# Anything not listed here appears alphabetically after.
FACET_VALUE_ORDER: dict[str, list[str]] = {
    "app_core_status": ["Core", "Candidate-Core"],
    "suggested_market_relevance": ["High", "Medium", "Low"],
    "suggested_economist_relevance": ["High", "Medium", "Low"],
}


def _row_value(row: Any, key: str) -> Any:
    """Read a value from a sqlite3.Row or any mapping-like object."""
    try:
        return row[key]
    except (KeyError, IndexError):
        return None


def _row_facet_value(row: Any, facet_key: str) -> str:
    """Normalized string value for a row/facet, used for comparisons."""
    raw = _row_value(row, facet_key)
    if raw is None:
        return ""
    text = str(raw).strip()
    return text


class FilterChip(QPushButton):
    """Small toggleable chip button used in the sidebar facet groups."""

    def __init__(self, value: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = value
        self._count = 0
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(
            "QPushButton {"
            " padding: 3px 8px;"
            " border: 1px solid #c0c0c0;"
            " border-radius: 10px;"
            " background: #ffffff;"
            " color: #333;"
            " font-size: 11px;"
            "}"
            "QPushButton:hover { background: #f0f0f0; }"
            "QPushButton:checked {"
            " background: #d6e4ff;"
            " border-color: #4a76d1;"
            " color: #14335c;"
            " font-weight: 600;"
            "}"
        )
        self._refresh_text()

    @property
    def value(self) -> str:
        return self._value

    def set_count(self, count: int) -> None:
        self._count = count
        self._refresh_text()

    def _refresh_text(self) -> None:
        label = self._value or "(unspecified)"
        self.setText(f"{label} ({self._count})")


class FlowContainer(QWidget):
    """Simple wrapping container for chips (uses HBox that wraps via QGridLayout-lite).

    QHBoxLayout doesn't wrap; a full flow layout is overkill here. We approximate
    wrapping by putting chips in successive rows once a row grows too wide. For the
    small facet counts we have, a single wrapping row via nested layouts is enough.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(4)
        self._current_row: QHBoxLayout | None = None
        self._current_row_width = 0
        self._max_row_width = 240

    def clear(self) -> None:
        while self._outer.count():
            item = self._outer.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
            else:
                layout = item.layout()
                if layout is not None:
                    while layout.count():
                        sub = layout.takeAt(0)
                        w = sub.widget()
                        if w is not None:
                            w.setParent(None)
        self._current_row = None
        self._current_row_width = 0

    def add_chip(self, chip: QWidget) -> None:
        chip_hint = chip.sizeHint().width()
        if self._current_row is None or self._current_row_width + chip_hint > self._max_row_width:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)
            row.addStretch(1)
            self._outer.addLayout(row)
            self._current_row = row
            self._current_row_width = 0

        # Insert before the trailing stretch (index count - 1).
        insert_at = max(0, self._current_row.count() - 1)
        self._current_row.insertWidget(insert_at, chip)
        self._current_row_width += chip_hint + 6


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
        self._settings = QSettings()

        # Selected chip values per facet key.
        self._selected: dict[str, set[str]] = {key: set() for key, _, _ in FACETS}

        # Populated on first sidebar build. facet_key -> {value: FilterChip}
        self._chips: dict[str, dict[str, FilterChip]] = {key: {} for key, _, _ in FACETS}
        self._facet_containers: dict[str, FlowContainer] = {}

        # Restore persisted chip selections before we build the UI.
        self._load_persisted_chip_selections()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        header = QLabel("<h2>Core Indicators</h2>")
        header.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(header)

        description = QLabel(
            "Browse the app's seeded FRED Core and Candidate-Core indicators. "
            "Use the sidebar chips to filter, then double-click a row (or select "
            "one and click Open Series) to view its chart."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #555;")
        layout.addWidget(description)

        toolbar = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(
            "Search by series ID, title, domain, frequency, or units..."
        )
        self.search_box.textChanged.connect(lambda _: self._apply_filters())
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
        self._rebuild_facet_chips()
        self._populate_table(self._rows)
        self._apply_filters()

    # ---------------------------------------------------------------- sidebar

    def _build_sidebar_widget(self) -> QWidget:
        """Build the sidebar with a scroll area, facet chip groups, and summary."""
        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(8)

        title = QLabel("<b>Core Indicators</b>")
        title.setTextFormat(Qt.TextFormat.RichText)
        outer_layout.addWidget(title)

        # Clear filters button, hidden until something is selected.
        self.clear_filters_button = QPushButton("Clear Filters")
        self.clear_filters_button.setVisible(False)
        self.clear_filters_button.clicked.connect(self._clear_all_chips)
        outer_layout.addWidget(self.clear_filters_button)

        # Scroll area for the facet groups (keeps the sidebar height manageable).
        scroll = QScrollArea()
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidgetResizable(True)
        outer_layout.addWidget(scroll, stretch=1)

        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(0, 0, 0, 0)
        inner_layout.setSpacing(10)
        scroll.setWidget(inner)

        for facet_key, facet_label, _settings_key in FACETS:
            group_label = QLabel(f"<b>{facet_label}</b>")
            group_label.setTextFormat(Qt.TextFormat.RichText)
            inner_layout.addWidget(group_label)

            container = FlowContainer()
            self._facet_containers[facet_key] = container
            inner_layout.addWidget(container)

        inner_layout.addStretch(1)

        # Sidebar summary shown at the bottom.
        self.sidebar_summary_label = QLabel("Catalog not loaded")
        self.sidebar_summary_label.setWordWrap(True)
        self.sidebar_summary_label.setStyleSheet("color: #666;")
        outer_layout.addWidget(self.sidebar_summary_label)

        return outer

    def _rebuild_facet_chips(self) -> None:
        """Rebuild the chip widgets from the currently-loaded rows."""
        for facet_key, _facet_label, _settings_key in FACETS:
            container = self._facet_containers.get(facet_key)
            if container is None:
                continue
            container.clear()
            self._chips[facet_key] = {}

            values = self._collect_facet_values(facet_key)
            for value in values:
                chip = FilterChip(value)
                if value in self._selected[facet_key]:
                    chip.setChecked(True)
                chip.toggled.connect(
                    lambda checked, k=facet_key, v=value: self._on_chip_toggled(k, v, checked)
                )
                container.add_chip(chip)
                self._chips[facet_key][value] = chip

    def _collect_facet_values(self, facet_key: str) -> list[str]:
        """Return sorted unique non-empty values for a facet, in display order."""
        raw_values: set[str] = set()
        for row in self._rows:
            v = _row_facet_value(row, facet_key)
            if v:
                raw_values.add(v)

        preferred = FACET_VALUE_ORDER.get(facet_key, [])
        ordered = [v for v in preferred if v in raw_values]
        ordered.extend(sorted(v for v in raw_values if v not in preferred))
        return ordered

    # ---------------------------------------------------------------- persistence

    def _load_persisted_chip_selections(self) -> None:
        """Restore chip selections from QSettings."""
        for facet_key, _facet_label, settings_key in FACETS:
            stored = self._settings.value(f"coreindicators/chips/{settings_key}", "", type=str)
            if not stored:
                continue
            values = {chunk for chunk in stored.split("\u001f") if chunk}
            self._selected[facet_key] = values

    def _persist_chip_selection(self, facet_key: str) -> None:
        settings_key = next(
            (sk for k, _lbl, sk in FACETS if k == facet_key),
            None,
        )
        if settings_key is None:
            return
        joined = "\u001f".join(sorted(self._selected[facet_key]))
        self._settings.setValue(f"coreindicators/chips/{settings_key}", joined)

    # ---------------------------------------------------------------- filtering

    def _on_chip_toggled(self, facet_key: str, value: str, checked: bool) -> None:
        selected = self._selected[facet_key]
        if checked:
            selected.add(value)
        else:
            selected.discard(value)
        self._persist_chip_selection(facet_key)
        self._apply_filters()

    def _clear_all_chips(self) -> None:
        for facet_key in self._selected:
            self._selected[facet_key] = set()
            self._persist_chip_selection(facet_key)
            for chip in self._chips[facet_key].values():
                # Block signals so we don't fire N re-filter passes.
                chip.blockSignals(True)
                chip.setChecked(False)
                chip.blockSignals(False)
        self._apply_filters()

    def _row_passes_chip_filters(self, row: Any) -> bool:
        for facet_key, selected in self._selected.items():
            if not selected:
                continue
            if _row_facet_value(row, facet_key) not in selected:
                return False
        return True

    def _row_passes_search(self, row: Any, needle: str) -> bool:
        if not needle:
            return True
        haystack_parts: list[str] = []
        for key in (
            "series_id",
            "title",
            "suggested_core_domain",
            "frequency",
            "units",
        ):
            v = _row_value(row, key)
            if v is not None:
                haystack_parts.append(str(v).lower())
        return needle in " | ".join(haystack_parts)

    def _apply_filters(self) -> None:
        """Recompute row visibility, chip counts, and sidebar summary."""
        needle = self.search_box.text().strip().lower()
        row_count = self.table.rowCount()

        visible_rows: list[Any] = []
        for i in range(row_count):
            item = self.table.item(i, 0)
            if item is None:
                self.table.setRowHidden(i, True)
                continue
            row = item.data(Qt.ItemDataRole.UserRole + 1)
            if row is None:
                self.table.setRowHidden(i, True)
                continue

            passes_chips = self._row_passes_chip_filters(row)
            passes_search = self._row_passes_search(row, needle)
            visible = passes_chips and passes_search
            self.table.setRowHidden(i, not visible)
            if visible:
                visible_rows.append(row)

        self._update_chip_counts(visible_rows)
        self._update_summary(visible_rows)
        self._update_sidebar_summary(visible_rows)

        any_selected = any(bool(v) for v in self._selected.values())
        self.clear_filters_button.setVisible(any_selected)

    def _update_chip_counts(self, visible_rows: Iterable[Any]) -> None:
        counts: dict[str, dict[str, int]] = {key: {} for key, _, _ in FACETS}
        for row in visible_rows:
            for facet_key in counts:
                v = _row_facet_value(row, facet_key)
                if not v:
                    continue
                counts[facet_key][v] = counts[facet_key].get(v, 0) + 1

        for facet_key, chip_map in self._chips.items():
            facet_counts = counts.get(facet_key, {})
            for value, chip in chip_map.items():
                chip.set_count(facet_counts.get(value, 0))

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
                # Series ID for signal emission and row lookup.
                item.setData(Qt.ItemDataRole.UserRole, _row_value(row, "series_id"))
                # Attach the full row (only on col 0) for filter lookups.
                if col_index == 0:
                    item.setData(Qt.ItemDataRole.UserRole + 1, row)
                if key == "popularity" and value is not None:
                    with contextlib.suppress(TypeError, ValueError):
                        item.setData(Qt.ItemDataRole.EditRole, int(value))
                self.table.setItem(row_index, col_index, item)

        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)

    def _update_summary(self, visible_rows: list[Any]) -> None:
        total_loaded = len(self._rows)
        visible = len(visible_rows)
        core_visible = sum(1 for r in visible_rows if _row_value(r, "app_core_status") == "Core")
        candidate_visible = sum(
            1 for r in visible_rows if _row_value(r, "app_core_status") == "Candidate-Core"
        )
        domain_visible = len(
            {
                _row_facet_value(r, "suggested_core_domain") or "Other/Unclassified"
                for r in visible_rows
            }
        )
        if total_loaded == 0:
            self.summary_label.setText("No indicators loaded.")
            return
        self.summary_label.setText(
            f"Showing {visible:,} of {total_loaded:,} indicators \u2014 "
            f"{core_visible:,} Core, {candidate_visible:,} Candidate-Core, "
            f"{domain_visible:,} domains."
        )

    def _update_sidebar_summary(self, visible_rows: list[Any]) -> None:
        if not visible_rows:
            self.sidebar_summary_label.setText("No indicators match the current filters.")
            return
        domain_counts: dict[str, int] = {}
        for row in visible_rows:
            domain = str(_row_value(row, "suggested_core_domain") or "Other/Unclassified")
            domain_counts[domain] = domain_counts.get(domain, 0) + 1
        top_domains = sorted(domain_counts.items(), key=lambda item: (-item[1], item[0]))[:6]
        lines: list[str] = [
            f"Showing {len(visible_rows):,} of {len(self._rows):,} indicators.",
            "",
        ]
        for domain, count in top_domains:
            lines.append(f"\u2022 {domain}: {count}")
        self.sidebar_summary_label.setText("\n".join(lines))

    # ---------------------------------------------------------------- interaction

    def _on_selection_changed(self) -> None:
        selection = self.table.selectionModel()
        has_row = selection is not None and selection.hasSelection()
        self.open_button.setEnabled(bool(has_row))

    def _selected_series_id(self) -> str | None:
        selection = self.table.selectionModel()
        if selection is None or not selection.hasSelection():
            return None
        indexes = selection.selectedRows()
        if not indexes:
            # SelectRows should give us row indexes, but fall back to the first column.
            indexes = selection.selectedIndexes()
        if not indexes:
            return None
        row = indexes[0].row()
        item = self.table.item(row, 0)
        if item is None:
            return None
        series_id = item.data(Qt.ItemDataRole.UserRole)
        if series_id is None:
            series_id = item.text()
        return str(series_id) if series_id else None

    def _open_selected_series(self) -> None:
        series_id = self._selected_series_id()
        if not series_id:
            return
        log.debug("CoreIndicatorsView: opening series %s", series_id)
        self.series_requested.emit(series_id)
