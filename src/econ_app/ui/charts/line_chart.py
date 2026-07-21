"""Single-series line chart widget using PyQtGraph.

Displays time-series observations with a date-aware x-axis and a numeric y-axis.
Handles missing values (gaps in the line) and empty state.
"""

from __future__ import annotations

from datetime import datetime

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QStackedLayout, QWidget

from econ_app.services.models import Observation, SeriesMetadata


class DateAxisItem(pg.AxisItem):
    """Custom axis that displays timestamps as human-readable dates."""

    def tickStrings(self, values: list[float], scale: float, spacing: float) -> list[str]:  # noqa: N802 (PyQtGraph override)
        # values are timestamps (seconds since epoch)
        strings = []
        for v in values:
            try:
                dt = datetime.fromtimestamp(v)
                # Show year only for widely-spaced ticks, else year-month
                if spacing >= 365 * 24 * 60 * 60:
                    strings.append(dt.strftime("%Y"))
                else:
                    strings.append(dt.strftime("%Y-%m"))
            except (ValueError, OverflowError):
                strings.append("")
        return strings


class LineChart(QWidget):
    """A single-series line chart with placeholder / loading / error / data states."""

    def __init__(self) -> None:
        super().__init__()

        # Configure PyQtGraph global defaults for this chart
        pg.setConfigOptions(antialias=True, background="w", foreground="#333")

        # The actual plot widget with custom date axis
        self._plot_widget = pg.PlotWidget(axisItems={"bottom": DateAxisItem(orientation="bottom")})
        self._plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self._plot_widget.setMouseEnabled(x=True, y=True)
        self._plot_widget.getPlotItem().setMenuEnabled(False)

        # Placeholder shown before data loads
        self._placeholder = QLabel("Loading...")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #888; font-size: 14px;")

        # Stack the two so we can swap between them
        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._stack.addWidget(self._placeholder)  # index 0
        self._stack.addWidget(self._plot_widget)  # index 1

        self._show_placeholder("Select a series to view")

    # ------------------------------------------------------------ public API

    def set_data(
        self, observations: list[Observation], metadata: SeriesMetadata | None = None
    ) -> None:
        """Render the given observations. Applies metadata to titles/labels if provided."""
        if not observations:
            self._show_placeholder("No data available for this series")
            return

        # Convert to timestamps + values, gapping missing observations
        timestamps: list[float] = []
        values: list[float] = []

        for obs in observations:
            if obs.is_missing or obs.value is None:
                # Gap: NaN causes PyQtGraph to break the line here
                timestamps.append(datetime.combine(obs.date, datetime.min.time()).timestamp())
                values.append(float("nan"))
            else:
                timestamps.append(datetime.combine(obs.date, datetime.min.time()).timestamp())
                values.append(obs.value)

        self._plot_widget.clear()
        self._plot_widget.plot(
            timestamps,
            values,
            pen=pg.mkPen(color="#1f77b4", width=2),
            connect="finite",  # skip NaN values (creates gaps)
        )
        self._plot_widget.getViewBox().autoRange()

        if metadata is not None:
            self._apply_metadata(metadata)

        self._stack.setCurrentIndex(1)  # Show plot

    def show_loading(self, message: str = "Loading data...") -> None:
        self._show_placeholder(message)

    def show_error(self, message: str) -> None:
        self._show_placeholder(f"Error: {message}")

    # -------------------------------------------------------------- internal

    def _show_placeholder(self, text: str) -> None:
        self._placeholder.setText(text)
        self._stack.setCurrentIndex(0)

    def _apply_metadata(self, metadata: SeriesMetadata) -> None:
        """Apply title, subtitle-like descriptor, and axis labels."""
        # PyQtGraph title
        self._plot_widget.setTitle(
            f"<b>{metadata.title}</b>",
            color="#222",
            size="12pt",
        )

        # Axis labels
        self._plot_widget.setLabel(
            "left",
            metadata.units_short or metadata.units,
            color="#555",
        )
        self._plot_widget.setLabel("bottom", "Date", color="#555")
