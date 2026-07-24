"""Core Indicators view.

Renders the committed FRED core-series seed catalog imported into SQLite.
Users can browse, search, filter by facet chips, and open any series in the
Series Detail view.

v0.6 bug fixes:
- FlowContainer no longer feedback-loops on resize
- Persisted chip selections that no longer match current data are pruned
  so a stale QSettings state can't hide every row
"""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from PySide6.QtCore import QEvent, QSettings, Qt, QTimer, Signal
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

FACETS: list[tuple[str, str, str]] = [
    ("app_core_status", "Core Status", "core_status"),
    ("suggested_core_domain", "Domain", "domain"),
    ("suggested_market_relevance", "Market Relevance", "market_relevance"),
    ("suggested_economist_relevance", "Economist Relevance", "economist_relevance"),
]

FACET_VALUE_ORDER: dict[str, list[str]] = {
    "app_core_status": ["Core", "Candidate-Core"],
    "suggested_market_relevance": ["High", "Medium", "Low"],
    "suggested_economist_relevance": ["High", "Medium", "Low"],
}


def _row_value(row: Any, key: str) -> Any:
    try:
        return row[key]
    except (KeyError, IndexError):
        return None


def _row_facet_value(row: Any, facet_key: str) -> str:
    raw = _row_value(row, facet_key)
    if raw is None:
        return ""
    text = str(raw).strip()
    return text


class FilterChip(QPushButton):
    """Small toggleable chip button."""

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
    """Wrapping container for chips.

    Lays out children into horizontal rows that wrap when the row would
    exceed the current widget width. Reflows on resize, debounced to avoid
    feedback loops from Qt's layout system.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._chips: list[QWidget] = []
        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 0)
        self._outer.setSpacing(4)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        self._last_layout_width = 0
        self._relayout_pending = False

    def clear(self) -> None:
        # Detach chips (we own them) and remove layouts (we recreate them).
        for chip in self._chips:
            chip.setParent(None)
        self._chips = []
        while self._outer.count():
            item = self._outer.takeAt(0)
            layout = item.layout()
            if layout is not None:
                # Remove any sub-widgets that may still be attached; then delete layout.
                while layout.count():
                    sub = layout.takeAt(0)
                    w = sub.widget()
                    if w is not None:
                        w.setParent(None)
        self._last_layout_width = 0

    def add_chip(self, chip: QWidget) -> None:
        self._chips.append(chip)
        # Immediate layout using current width.
        self._do_relayout(force=True)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._schedule_relayout()

    def _schedule_relayout(self) -> None:
        if self._relayout_pending:
            return
        self._relayout_pending = True
        # Defer to next event loop turn so we don't recurse during Qt's layout pass.
        QTimer.singleShot(0, self._do_relayout)

    def _available_width(self) -> int:
        width = self.width()
        if width <= 0:
            parent = self.parentWidget()
            if parent is not None:
                width = parent.width()
        return max(width, 160)

    def _do_relayout(self, force: bool = False) -> None:
        self._relayout_pending = False

        available = self._available_width()
        # If nothing meaningful changed, skip work to avoid feedback loops.
        if not force and abs(available - self._last_layout_width) < 4:
            return
        self._last_layout_width = available

        # Detach chips from any layouts they're currently in.
        for chip in self._chips:
            chip.setParent(self)  # detach from prior HBox, reparent to us
            chip.show()

        # Clear existing row layouts.
        while self._outer.count():
            item = self._outer.takeAt(0)
            layout = item.layout()
            if layout is not None:
                while layout.count():
                    layout.takeAt(0)

        # Repack chips into new rows.
        current_row: QHBoxLayout | None = None
        current_width = 0

        for chip in self._chips:
            chip_width = chip.sizeHint().width()
            if current_row is None or current_width + chip_width > available:
                row = QHBoxLayout()
                row.setContentsMargins(0, 0, 0, 0)
                row.setSpacing(4)
                row.addStretch(1)
                self._outer.addLayout(row)
                current_row = row
                current_width = 0

            insert_at = max(0, current_row.count() - 1)
            current_row.insertWidget(insert_at, chip)
            current_width += chip_width + 6


class CoreIndicatorsView(BaseView):
    """Core Indicators content view."""

    view_name = "Core Indicators"

    series_requested = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._rows: list[Any] = []
        self._loaded = False
        self._settings = QSettings()

        # State for chip filtering.
        self._selected: dict[str, set[str]] = {key: set() for key, _, _ in FACETS}
        self._chips: dict[str, dict[str, FilterChip]] = {key: {} for key, _, _ in FACETS}
        self._facet_containers: dict[str, FlowContainer] = {}
        self._load_persisted_chip_selections()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        # Header + description
        header = QLabel("<h2>Core Indicators</h2>")
        header.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(header)

        description = QLabel(
            "Browse the app's seeded FRED Core and Candidate-Core indicators. "
            "Use the sidebar chips to filter, then double-click a row (or "
            "select one and click Open Series) to view its chart."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #555;")
        layout.addWidget(description)

        # Search + Open Series row
        search_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(
            "Search by series ID, title, domain, frequency, or units..."
        )
        self.search_box.textChanged.connect(lambda _text: self._apply_filters())
        search_row.addWidget(self.search_box, stretch=1)

        self.open_button = QPushButton("Open Series")
        self.open_button.setEnabled(False)
        self.open_button.clicked.connect(self._open_selected_series)
        search_row.addWidget(self.open_button)
        layout.addLayout(search_row)

        # Summary line
        self.summary_label = QLabel("Loading catalog...")
        self.summary_label.setStyleSheet("color: #444; font-size: 12px;")
        layout.addWidget(self.summary_label)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(len(TABLE_COLUMNS))
        self.table.setHorizontalHeaderLabels([label for _key, label in TABLE_COLUMNS])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.itemDoubleClicked.connect(lambda _i: self._open_selected_series())
        layout.addWidget(self.table, stretch=1)

        # Build the sidebar widget (BaseView contract)
        self.sidebar_widget = self._build_sidebar_widget()

    def ensure_loaded(self) -> None:
        if self._loaded:
            return
        self.reload()

    def reload(self) -> None:
        try:
            with get_connection() as conn:
                self._rows = list(list_core_series(conn, limit=1_000))
        except Exception as exc:  # pragma: no cover - defensive UI boundary
            log.exception("Failed to load core indicators")
            self._rows = []
            self.summary_label.setText(f"Could not load core indicators: {exc}")
            self.table.setRowCount(0)
            self._loaded = False
            return

        self._loaded = True
        self._prune_stale_selections()
        self._rebuild_facet_chips()
        self._populate_table()
        self._apply_filters()

    def _prune_stale_selections(self) -> None:
        """Drop persisted chip values that don't appear in the current data.

        Prevents a stale QSettings state from a previous session or schema
        from hiding every row.
        """
        for key, _label, _ in FACETS:
            valid = {_row_facet_value(r, key) for r in self._rows}
            self._selected[key] = {v for v in self._selected[key] if v in valid}

    def _build_sidebar_widget(self) -> QWidget:
        outer = QWidget()
        outer.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        content = QWidget()
        content.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(8)

        title = QLabel("<b>Core Indicators</b>")
        title.setTextFormat(Qt.TextFormat.RichText)
        content_layout.addWidget(title)

        self.sidebar_hint = QLabel("Click chips below to filter the table.")
        self.sidebar_hint.setWordWrap(True)
        self.sidebar_hint.setStyleSheet("color: #666; font-size: 11px;")
        content_layout.addWidget(self.sidebar_hint)

        self.clear_filters_button = QPushButton("Clear Filters")
        self.clear_filters_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_filters_button.clicked.connect(self._clear_filters)
        self.clear_filters_button.setVisible(False)
        content_layout.addWidget(self.clear_filters_button)

        for key, label, _ in FACETS:
            group_label = QLabel(f"<b>{label}</b>")
            group_label.setTextFormat(Qt.TextFormat.RichText)
            content_layout.addWidget(group_label)

            container = FlowContainer()
            self._facet_containers[key] = container
            content_layout.addWidget(container)

        self.sidebar_summary_label = QLabel("Catalog not loaded")
        self.sidebar_summary_label.setWordWrap(True)
        self.sidebar_summary_label.setStyleSheet("color: #555; font-size: 11px;")
        content_layout.addWidget(self.sidebar_summary_label)

        content_layout.addStretch(1)
        scroll.setWidget(content)

        outer_layout.addWidget(scroll)
        return outer

    def _rebuild_facet_chips(self) -> None:
        for key, _label, _ in FACETS:
            container = self._facet_containers.get(key)
            if container is None:
                continue
            container.clear()
            self._chips[key] = {}

            seen: dict[str, int] = {}
            for row in self._rows:
                val = _row_facet_value(row, key)
                seen[val] = seen.get(val, 0) + 1

            order = FACET_VALUE_ORDER.get(key, [])
            ordered: list[str] = []
            for preferred in order:
                if preferred in seen and preferred not in ordered:
                    ordered.append(preferred)
            for value in sorted(seen):
                if value not in ordered:
                    ordered.append(value)

            for value in ordered:
                chip = FilterChip(value)
                chip.set_count(seen.get(value, 0))
                chip.setChecked(value in self._selected[key])
                chip.toggled.connect(self._make_chip_handler(key, value))
                container.add_chip(chip)
                self._chips[key][value] = chip

    def _make_chip_handler(self, facet_key: str, value: str):
        def handler(checked: bool) -> None:
            if checked:
                self._selected[facet_key].add(value)
            else:
                self._selected[facet_key].discard(value)
            self._persist_chip_selections()
            self._apply_filters()

        return handler

    def _clear_filters(self) -> None:
        for key in list(self._selected):
            if self._selected[key]:
                self._selected[key] = set()
        for key in self._chips:
            for chip in self._chips[key].values():
                chip.setChecked(False)
        self.search_box.clear()
        self._persist_chip_selections()
        self._apply_filters()

    def _populate_table(self) -> None:
        sorted_rows = sorted(
            self._rows,
            key=lambda row: (
                STATUS_SORT_ORDER.get(str(_row_value(row, "app_core_status") or ""), 99),
                -int(_row_value(row, "candidate_core_score") or 0),
                -int(_row_value(row, "popularity") or 0),
                str(_row_value(row, "series_id") or ""),
            ),
        )

        self.table.setSortingEnabled(False)
        self.table.setRowCount(len(sorted_rows))

        for row_index, row in enumerate(sorted_rows):
            for col_index, (key, _label) in enumerate(TABLE_COLUMNS):
                value = _row_value(row, key)
                item = QTableWidgetItem("" if value is None else str(value))
                item.setData(Qt.ItemDataRole.UserRole, _row_value(row, "series_id"))
                if key == "popularity" and value is not None:
                    with contextlib.suppress(TypeError, ValueError):
                        item.setData(Qt.ItemDataRole.EditRole, int(value))
                self.table.setItem(row_index, col_index, item)

        self.table.resizeColumnsToContents()
        self.table.setSortingEnabled(True)

    def _apply_filters(self) -> None:
        search_text = self.search_box.text().strip().lower()
        search_terms = [t for t in search_text.split() if t]

        any_chip_selected = any(self._selected[key] for key in self._selected)
        self.clear_filters_button.setVisible(bool(any_chip_selected or search_text))

        series_id_col = 0
        row_count = self.table.rowCount()
        visible: list[Any] = []

        for row_index in range(row_count):
            series_item = self.table.item(row_index, series_id_col)
            if series_item is None:
                self.table.setRowHidden(row_index, True)
                continue
            series_id = series_item.text()
            row = self._find_row_by_id(series_id)
            if row is None:
                self.table.setRowHidden(row_index, True)
                continue

            show = True
            for key in self._selected:
                chip_selections = self._selected[key]
                if not chip_selections:
                    continue
                row_value = _row_facet_value(row, key)
                if row_value not in chip_selections:
                    show = False
                    break

            if show and search_terms:
                haystack = " ".join(
                    str(_row_value(row, key) or "") for key, _ in TABLE_COLUMNS
                ).lower()
                for term in search_terms:
                    if term not in haystack:
                        show = False
                        break

            self.table.setRowHidden(row_index, not show)
            if show:
                visible.append(row)

        self._update_summary(visible)
        self._update_sidebar_summary(visible)
        self._update_chip_counts(visible)

    def _update_summary(self, visible: list[Any]) -> None:
        total = len(self._rows)
        showing = len(visible)
        core = sum(1 for row in visible if _row_value(row, "app_core_status") == "Core")
        candidate = sum(
            1 for row in visible if _row_value(row, "app_core_status") == "Candidate-Core"
        )
        domains = sorted({str(_row_value(row, "suggested_core_domain") or "") for row in visible})
        self.summary_label.setText(
            f"Showing {showing:,} of {total:,} indicators — "
            f"{core:,} Core, {candidate:,} Candidate-Core, "
            f"{len(domains):,} domains visible."
        )

    def _update_sidebar_summary(self, visible: list[Any]) -> None:
        if not visible:
            self.sidebar_summary_label.setText("No indicators match the current filters.")
            return

        domain_counts: dict[str, int] = {}
        for row in visible:
            domain = str(_row_value(row, "suggested_core_domain") or "Other/Unclassified")
            domain_counts[domain] = domain_counts.get(domain, 0) + 1

        top = sorted(domain_counts.items(), key=lambda pair: (-pair[1], pair[0]))[:8]
        lines = [f"Showing {len(visible):,} of {len(self._rows):,} indicators."]
        lines.append("")
        lines.extend(f"• {domain}: {count}" for domain, count in top)
        self.sidebar_summary_label.setText("\n".join(lines))

    def _update_chip_counts(self, visible: list[Any]) -> None:
        for key, chips in self._chips.items():
            counts = {value: 0 for value in chips}
            for row in visible:
                val = _row_facet_value(row, key)
                if val in counts:
                    counts[val] += 1
            for value, chip in chips.items():
                chip.set_count(counts.get(value, 0))

    def _find_row_by_id(self, series_id: str) -> Any:
        for row in self._rows:
            if str(_row_value(row, "series_id")) == series_id:
                return row
        return None

    def _on_selection_changed(self) -> None:
        has_row = self.table.selectionModel().hasSelection()
        self.open_button.setEnabled(has_row)

    def _open_selected_series(self) -> None:
        selection = self.table.selectionModel().selectedRows()
        if not selection:
            return
        row = selection[0].row()
        item = self.table.item(row, 0)
        if item is None:
            return
        series_id = item.text()
        if series_id:
            log.info("Core Indicators opening series: %s", series_id)
            self.series_requested.emit(series_id)

    def _persist_chip_selections(self) -> None:
        for key, _label, settings_key in FACETS:
            self._settings.setValue(
                f"coreindicators/chips/{settings_key}", sorted(self._selected[key])
            )

    def _load_persisted_chip_selections(self) -> None:
        for key, _label, settings_key in FACETS:
            raw = self._settings.value(f"coreindicators/chips/{settings_key}", [])
            if raw is None:
                continue
            if isinstance(raw, str):
                raw = [raw]
            self._selected[key] = {str(v) for v in raw}

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802
        super().changeEvent(event)
