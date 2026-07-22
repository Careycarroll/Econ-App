"""Series Detail view — chart-viewing experience with controls and transforms.

Displays a single FRED series with metadata, chart, controls, attribution, and
last-synced info. In v0.4, the series is hardcoded to CPIAUCSL. Explorer (v0.5)
will drive series selection.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from PySide6.QtCore import QSettings, Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from econ_app.services.app_cache import get_app_cache
from econ_app.services.fred_client import FREDAPIError
from econ_app.services.models import SeriesMetadata
from econ_app.services.transforms import (
    TRANSFORM_LEVEL,
    TRANSFORMS,
    apply_transform,
    is_applicable,
)
from econ_app.ui.charts.line_chart import LineChart
from econ_app.ui.views.base_view import BaseView

log = logging.getLogger(__name__)

DEFAULT_SERIES_ID = "CPIAUCSL"


class SeriesDetailView(BaseView):
    """Series Detail view with chart controls and transforms."""

    view_name = "Series Detail"

    def __init__(self) -> None:
        super().__init__()

        self._series_id: str | None = None
        self._metadata: SeriesMetadata | None = None
        self._observations: list = []
        self._loaded = False
        self._current_transform = TRANSFORM_LEVEL
        self._current_range = "5Y"
        self._preset_buttons: dict[str, QPushButton] = {}

        # Scrollable inner widget
        self._inner = QWidget()
        inner_layout = QVBoxLayout(self._inner)
        inner_layout.setContentsMargins(24, 24, 24, 24)
        inner_layout.setSpacing(16)

        # 1. Header block
        self._title_label = QLabel("")
        self._title_label.setStyleSheet("font-size: 18px; font-weight: 600; color: #222;")
        self._title_label.setWordWrap(True)

        self._meta_label = QLabel("")
        self._meta_label.setStyleSheet("font-size: 12px; color: #666;")
        self._meta_label.setWordWrap(True)

        inner_layout.addWidget(self._title_label)
        inner_layout.addWidget(self._meta_label)

        # 2. Chart controls row
        controls_row = self._build_controls_row()
        inner_layout.addLayout(controls_row)

        # 3. Chart
        self._chart = LineChart()
        self._chart.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._chart.setMinimumHeight(400)
        inner_layout.addWidget(self._chart)

        # 4. Attribution + timestamp
        attribution_box = QFrame()
        attribution_box.setStyleSheet("QFrame { border-top: 1px solid #eee; padding-top: 8px; }")
        attribution_layout = QVBoxLayout(attribution_box)
        attribution_layout.setContentsMargins(0, 8, 0, 0)
        attribution_layout.setSpacing(2)

        self._attribution_label = QLabel("")
        self._attribution_label.setStyleSheet("font-size: 11px; color: #888;")
        self._attribution_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        self._timestamp_label = QLabel("")
        self._timestamp_label.setStyleSheet("font-size: 11px; color: #888;")

        attribution_layout.addWidget(self._attribution_label)
        attribution_layout.addWidget(self._timestamp_label)
        inner_layout.addWidget(attribution_box)

        # 5. Learning content placeholder
        learning_placeholder = QLabel(
            "Learning content — coming in v0.8 "
            "(three-tier descriptions, market impact, release schedule)"
        )
        learning_placeholder.setStyleSheet(
            "color: #aaa; font-size: 11px; padding: 8px; "
            "border: 1px dashed #ddd; border-radius: 4px;"
        )
        learning_placeholder.setWordWrap(True)
        inner_layout.addWidget(learning_placeholder)

        inner_layout.addStretch(1)

        # Wrap in QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(self._inner)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(scroll)

        # Sidebar
        self.sidebar_widget = QLabel(
            "Series navigation\n\nExplorer (v0.5) will show the\n"
            "Category → Release → Series tree here."
        )
        self.sidebar_widget.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.sidebar_widget.setStyleSheet("color: #666; padding: 8px;")

    # ------------------------------------------------------------ controls

    def _build_controls_row(self) -> QHBoxLayout:
        """Build the row of chart controls."""
        row = QHBoxLayout()
        row.setContentsMargins(0, 4, 0, 4)
        row.setSpacing(8)

        # Date range preset buttons
        range_group = QButtonGroup(self)
        range_group.setExclusive(True)
        for label in ("1Y", "5Y", "10Y", "MAX"):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setStyleSheet(
                "QPushButton { padding: 4px 12px; border: 1px solid #c0c0c0; }"
                "QPushButton:checked { background-color: #e0e0e0; "
                "font-weight: 600; }"
            )
            btn.clicked.connect(lambda _checked=False, label_val=label: self._set_range(label_val))
            range_group.addButton(btn)
            row.addWidget(btn)
            self._preset_buttons[label] = btn

        # Custom range button
        custom_btn = QPushButton("Custom...")
        custom_btn.setFixedHeight(28)
        custom_btn.clicked.connect(self._open_custom_range_dialog)
        row.addWidget(custom_btn)

        row.addStretch(1)

        # Transform selector
        transform_label = QLabel("Transform:")
        transform_label.setStyleSheet("color: #555;")
        row.addWidget(transform_label)

        self._transform_combo = QComboBox()
        self._transform_combo.setFixedHeight(28)
        for opt in TRANSFORMS:
            self._transform_combo.addItem(opt.label, opt.key)
        self._transform_combo.currentIndexChanged.connect(self._on_transform_changed)
        row.addWidget(self._transform_combo)

        return row

    # ------------------------------------------------------------ public API

    def load_series(self, series_id: str, force_refresh: bool = False) -> None:
        """Load and display the given series."""
        log.info("load_series(%s, force_refresh=%s)", series_id, force_refresh)
        self._series_id = series_id
        self._chart.show_loading(f"Loading {series_id}...")

        try:
            cache = get_app_cache()
        except RuntimeError as e:
            log.error("Cannot init cache: %s", e)
            self._show_config_error()
            return

        try:
            metadata = cache.get_metadata(series_id, force_refresh=force_refresh)
            observations = cache.get_observations(series_id, force_refresh=force_refresh)
        except FREDAPIError as e:
            log.error("FRED error loading %s: %s", series_id, e)
            self._chart.show_error(str(e))
            self._title_label.setText(f"Could not load {series_id}")
            self._meta_label.setText("")
            self._attribution_label.setText("")
            self._timestamp_label.setText("")
            return

        self._metadata = metadata
        self._observations = observations
        self._render_metadata(metadata)

        self._load_settings()
        self._update_transform_availability()
        self._render_observations()

        last_synced = cache.get_last_synced(series_id)
        self._render_timestamps(metadata, last_synced)
        self._loaded = True

    def ensure_loaded(self) -> None:
        """Trigger a load on first activation of this view."""
        log.debug(
            "ensure_loaded called: _loaded=%s _series_id=%s",
            self._loaded,
            self._series_id,
        )
        if not self._loaded and self._series_id is None:
            log.debug("ensure_loaded: triggering initial load of %s", DEFAULT_SERIES_ID)
            self.load_series(DEFAULT_SERIES_ID)

    def refresh_current(self) -> None:
        """Force-refresh the currently displayed series from FRED."""
        if self._series_id:
            self.load_series(self._series_id, force_refresh=True)

    # -------------------------------------------------------------- controls

    def _set_range(self, label: str) -> None:
        """Apply a preset date range."""
        self._current_range = label
        if label in self._preset_buttons:
            self._preset_buttons[label].setChecked(True)
        if self._series_id:
            self._save_setting("date_range", label)
        self._apply_view_range()

    def _apply_view_range(self) -> None:
        """Set the chart's x-axis range according to self._current_range."""
        if not self._observations:
            return

        now = datetime.now().timestamp()
        if self._current_range == "1Y":
            start = datetime.now().replace(year=datetime.now().year - 1).timestamp()
        elif self._current_range == "5Y":
            start = datetime.now().replace(year=datetime.now().year - 5).timestamp()
        elif self._current_range == "10Y":
            start = datetime.now().replace(year=datetime.now().year - 10).timestamp()
        else:  # MAX
            self._chart._plot_widget.getViewBox().autoRange()
            return

        self._chart._plot_widget.setXRange(start, now, padding=0.02)

    def _open_custom_range_dialog(self) -> None:
        """Show a modal dialog to pick a custom date range."""
        if not self._observations:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Custom date range")
        dialog.setModal(True)

        min_date = self._observations[0].date
        max_date = self._observations[-1].date

        start_edit = QDateEdit()
        start_edit.setCalendarPopup(True)
        start_edit.setDate(min_date)
        start_edit.setMinimumDate(min_date)
        start_edit.setMaximumDate(max_date)

        end_edit = QDateEdit()
        end_edit.setCalendarPopup(True)
        end_edit.setDate(max_date)
        end_edit.setMinimumDate(min_date)
        end_edit.setMaximumDate(max_date)

        form = QFormLayout()
        form.addRow("Start:", start_edit)
        form.addRow("End:", end_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)

        outer = QVBoxLayout(dialog)
        outer.addLayout(form)
        outer.addWidget(buttons)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            start_ts = datetime.combine(
                start_edit.date().toPython(), datetime.min.time()
            ).timestamp()
            end_ts = datetime.combine(end_edit.date().toPython(), datetime.min.time()).timestamp()
            self._chart._plot_widget.setXRange(start_ts, end_ts, padding=0.02)
            for btn in self._preset_buttons.values():
                btn.setChecked(False)
            self._current_range = "custom"

    def _on_transform_changed(self, index: int) -> None:
        """User picked a new transform from the dropdown."""
        if index < 0:
            return
        key = self._transform_combo.itemData(index)
        self._current_transform = key
        if self._series_id:
            self._save_setting("transform", key)
        self._render_observations()

    def _render_observations(self) -> None:
        """Apply current transform and push observations to the chart."""
        if not self._observations or not self._metadata:
            return
        transformed = apply_transform(
            self._observations,
            self._current_transform,
            frequency_short=self._metadata.frequency_short,
        )
        self._chart.set_data(transformed, self._metadata)
        self._apply_view_range()

    def _update_transform_availability(self) -> None:
        """Grey-out transforms that don't apply to this series."""
        if not self._metadata:
            return
        model = self._transform_combo.model()
        for i in range(self._transform_combo.count()):
            key = self._transform_combo.itemData(i)
            applicable = is_applicable(key, self._metadata)
            item = model.item(i)
            if item is not None:
                item.setEnabled(applicable)

    # -------------------------------------------------------------- persistence

    def _save_setting(self, key: str, value: str) -> None:
        s = QSettings()
        s.setValue(f"series/{self._series_id}/{key}", value)

    def _load_settings(self) -> None:
        """Restore per-series settings."""
        s = QSettings()
        saved_range = s.value(f"series/{self._series_id}/date_range", "5Y", type=str)
        saved_transform = s.value(f"series/{self._series_id}/transform", TRANSFORM_LEVEL, type=str)

        self._current_range = saved_range if saved_range in ("1Y", "5Y", "10Y", "MAX") else "5Y"
        self._current_transform = saved_transform

        if self._current_range in self._preset_buttons:
            self._preset_buttons[self._current_range].setChecked(True)
        for i in range(self._transform_combo.count()):
            if self._transform_combo.itemData(i) == self._current_transform:
                self._transform_combo.blockSignals(True)
                self._transform_combo.setCurrentIndex(i)
                self._transform_combo.blockSignals(False)
                break

    # -------------------------------------------------------------- rendering

    def _render_metadata(self, metadata: SeriesMetadata) -> None:
        self._title_label.setText(metadata.title)
        parts = [
            metadata.units,
            metadata.seasonal_adjustment,
            metadata.frequency,
        ]
        self._meta_label.setText(" · ".join(p for p in parts if p))

    def _render_timestamps(self, metadata: SeriesMetadata, last_synced: datetime | None) -> None:
        agency = _extract_agency(metadata.notes) or "the source agency"
        self._attribution_label.setText(f"Source: {agency} via FRED. Series ID: {metadata.id}")
        last_synced_str = _format_relative(last_synced) if last_synced else "never"
        fred_updated_str = _format_relative(metadata.last_updated)
        self._timestamp_label.setText(
            f"Last synced: {last_synced_str}  ·  FRED last updated: {fred_updated_str}"
        )

    def _show_config_error(self) -> None:
        self._chart.show_error("No FRED API key configured. Add FRED_API_KEY to .env and restart.")
        self._title_label.setText("Configuration needed")
        self._meta_label.setText("")
        self._attribution_label.setText("")
        self._timestamp_label.setText("")


def _extract_agency(notes: str | None) -> str | None:
    """Try to find the source agency in a FRED notes field."""
    if not notes:
        return None
    known = [
        "Bureau of Labor Statistics",
        "Bureau of Economic Analysis",
        "U.S. Census Bureau",
        "Federal Reserve",
        "U.S. Department of the Treasury",
        "Energy Information Administration",
    ]
    for agency in known:
        if agency in notes:
            return agency
    return None


def _format_relative(dt: datetime) -> str:
    """Format a datetime as a relative timestamp."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    delta = now - dt
    seconds = int(delta.total_seconds())

    if seconds < 60:
        return "just now"
    if seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    if seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    if seconds < 86400 * 30:
        days = seconds // 86400
        return f"{days} day{'s' if days != 1 else ''} ago"
    if seconds < 86400 * 365:
        months = seconds // (86400 * 30)
        return f"{months} month{'s' if months != 1 else ''} ago"
    years = seconds // (86400 * 365)
    return f"{years} year{'s' if years != 1 else ''} ago"
