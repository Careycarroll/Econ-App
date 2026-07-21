"""Series Detail view — the primary chart-viewing experience.

Displays a single FRED series with metadata, chart, attribution, and last-synced info.
In v0.4, the series is hardcoded to CPIAUCSL. Explorer (v0.5) will drive the choice.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from econ_app.services.app_cache import get_app_cache
from econ_app.services.fred_client import FREDAPIError
from econ_app.services.models import SeriesMetadata
from econ_app.ui.charts.line_chart import LineChart
from econ_app.ui.views.base_view import BaseView

log = logging.getLogger(__name__)

# v0.4 default series. Explorer (v0.5) will let the user pick.
DEFAULT_SERIES_ID = "CPIAUCSL"


class SeriesDetailView(BaseView):
    """The Series Detail view.

    Layout (top to bottom, scrollable):
      1. Header block (title + metadata line)
      2. Chart controls (empty in v0.4, populated in later issues)
      3. Chart
      4. Attribution + last-synced info
      5. Learning content (empty in v0.4, populated in v0.8)
    """

    view_name = "Series Detail"

    def __init__(self) -> None:
        super().__init__()

        self._series_id: str | None = None
        self._metadata: SeriesMetadata | None = None
        self._loaded = False

        # Build the scrollable inner widget
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

        # 2. Chart controls placeholder (later issues fill this in)
        self._controls_placeholder = QLabel(
            "Date range / transform / compare controls — coming in later v0.4 issues"
        )
        self._controls_placeholder.setStyleSheet(
            "color: #aaa; font-size: 11px; padding: 8px; "
            "border: 1px dashed #ddd; border-radius: 4px;"
        )
        inner_layout.addWidget(self._controls_placeholder)

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
            "Learning content — coming in v0.8 (three-tier descriptions, market impact, release schedule)"
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

    # ------------------------------------------------------------ public API

    def load_series(self, series_id: str, force_refresh: bool = False) -> None:
        """Load and display the given series.

        Fetches from cache; on cache miss fetches from FRED (blocking on main thread
        for v0.4). Handles errors gracefully.
        """
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

        # Populate everything
        self._metadata = metadata
        self._render_metadata(metadata)
        self._chart.set_data(observations, metadata)

        last_synced = cache.get_last_synced(series_id)
        self._render_timestamps(metadata, last_synced)
        self._loaded = True

    def ensure_loaded(self) -> None:
        """Trigger a load on first activation of this view."""
        log.debug("ensure_loaded called: _loaded=%s _series_id=%s", self._loaded, self._series_id)
        if not self._loaded and self._series_id is None:
            log.debug("ensure_loaded: triggering initial load of %s", DEFAULT_SERIES_ID)
            self.load_series(DEFAULT_SERIES_ID)
        else:
            log.debug("ensure_loaded: guard blocked load")

    def refresh_current(self) -> None:
        """Force-refresh the currently displayed series from FRED."""
        if self._series_id:
            self.load_series(self._series_id, force_refresh=True)

    # -------------------------------------------------------------- internal

    def _render_metadata(self, metadata: SeriesMetadata) -> None:
        self._title_label.setText(metadata.title)
        parts = [
            metadata.units,
            metadata.seasonal_adjustment,
            metadata.frequency,
        ]
        self._meta_label.setText(" · ".join(p for p in parts if p))

    def _render_timestamps(self, metadata: SeriesMetadata, last_synced: datetime | None) -> None:
        # Attribution: try to extract source agency from notes, fall back to FRED
        agency = _extract_agency(metadata.notes) or "the source agency"
        self._attribution_label.setText(f"Source: {agency} via FRED. Series ID: {metadata.id}")

        # Timestamps
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
    """Try to find the source agency in a FRED notes field.

    FRED notes commonly mention 'Bureau of Labor Statistics', 'Federal Reserve', etc.
    Simple heuristic — not exhaustive.
    """
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
    """Format a datetime as a relative timestamp (e.g., '3 hours ago')."""
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
