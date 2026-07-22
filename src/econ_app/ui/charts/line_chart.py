"""Single-series line chart widget using PyQtGraph.

Displays time-series observations with a date-aware x-axis and a numeric y-axis.
Handles missing values (gaps in the line) and empty state.
"""

from __future__ import annotations

from datetime import datetime

import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal
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

    reset_view_requested = Signal()

    def __init__(self) -> None:
        super().__init__()

        # Configure PyQtGraph global defaults for this chart
        pg.setConfigOptions(antialias=True, background="w", foreground="#333")

        # The actual plot widget with custom date axis
        self._plot_widget = pg.PlotWidget(axisItems={"bottom": DateAxisItem(orientation="bottom")})
        self._plot_widget.showGrid(x=True, y=True, alpha=0.2)
        self._plot_widget.setMouseEnabled(x=True, y=True)
        self._plot_widget.getPlotItem().setMenuEnabled(False)

        # Crosshair overlay
        self._crosshair_v = pg.InfiniteLine(
            angle=90, movable=False, pen=pg.mkPen("#666", width=0.5)
        )
        self._crosshair_h = pg.InfiniteLine(angle=0, movable=False, pen=pg.mkPen("#666", width=0.5))
        self._crosshair_v.hide()
        self._crosshair_h.hide()
        self._plot_widget.addItem(self._crosshair_v, ignoreBounds=True)
        self._plot_widget.addItem(self._crosshair_h, ignoreBounds=True)

        self._crosshair_label = pg.TextItem(anchor=(0, 1), color="#333")
        self._crosshair_label.hide()
        self._plot_widget.addItem(self._crosshair_label, ignoreBounds=True)

        # Wire mouse tracking on the scene
        self._proxy = pg.SignalProxy(
            self._plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_mouse_moved,
        )

        # Right-click resets view (per Issue #41)
        self._plot_widget.scene().sigMouseClicked.connect(self._on_mouse_clicked)

        # Cache observations for crosshair lookup
        self._observation_dates: list = []
        self._observation_values: list = []

        # Placeholder shown before data loads
        self._placeholder = QLabel("Loading...")
        self._placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._placeholder.setStyleSheet("color: #888; font-size: 14px;")

        # Stack the two so we can swap between them
        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)
        self._stack.addWidget(self._placeholder)
        self._stack.addWidget(self._plot_widget)

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

    def _on_mouse_moved(self, event) -> None:
        pos = event[0]
        vb = self._plot_widget.getPlotItem().getViewBox()
        if not self._plot_widget.sceneBoundingRect().contains(pos):
            self._crosshair_v.hide()
            self._crosshair_h.hide()
            self._crosshair_label.hide()
            return
        mouse_point = vb.mapSceneToView(pos)
        self._crosshair_v.setPos(mouse_point.x())
        self._crosshair_h.setPos(mouse_point.y())
        self._crosshair_v.show()
        self._crosshair_h.show()

        from datetime import datetime as _dt

        try:
            date_str = _dt.fromtimestamp(mouse_point.x()).strftime("%Y-%m-%d")
        except (ValueError, OverflowError):
            date_str = "?"

        value_str = self._nearest_value(mouse_point.x())
        self._crosshair_label.setText(f"{date_str}\n{value_str}")
        self._crosshair_label.setPos(mouse_point.x(), mouse_point.y())
        self._crosshair_label.show()

    def _nearest_value(self, x_timestamp: float) -> str:
        if not self._observation_dates:
            return "?"
        from datetime import datetime as _dt

        try:
            target = _dt.fromtimestamp(x_timestamp).date()
        except (ValueError, OverflowError):
            return "?"
        nearest_idx = min(
            range(len(self._observation_dates)),
            key=lambda i: abs((self._observation_dates[i] - target).days),
        )
        v = self._observation_values[nearest_idx]
        if v is None:
            return "(missing)"
        return f"{v:.2f}"

    def _on_mouse_clicked(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            self._plot_widget.getViewBox().autoRange()
            self.reset_view_requested.emit()
