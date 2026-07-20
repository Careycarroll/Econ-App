"""View classes for the main content area.

- MyCalendarView (default, ⌘1): FRED-backed personal calendar. Placeholder until
  v0.3 (FRED client) and v0.7 (real implementation) land.
- ExplorerView (⌘2): browse the FRED catalog. Placeholder until v0.5.
- SeriesDetailView (⌘3): single-series chart with controls. Placeholder until v0.4.
- CoreIndicatorsView (⌘4): Baumohl-based curated list. Placeholder until v0.6.
- MarketCalendarView (⌘5): Investing.com Economic Calendar widget. Live now.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from econ_app.ui.views.base_view import BaseView

INVESTING_COM_CALENDAR_URL = (
    "https://sslecal2.investing.com"
    "?columns=exc_flags,exc_currency,exc_importance,exc_actual,exc_forecast,exc_previous"
    "&features=datepicker,timezone,timeselector,filters"
    "&countries=5"
    "&importance=3"
    "&timeZone=8"
    "&lang=1"
)


def _make_placeholder(text: str, subtext: str) -> QLabel:
    label = QLabel(f"<h2>{text}</h2><p style='color:#666;'>{subtext}</p>")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setTextFormat(Qt.TextFormat.RichText)
    return label


def _make_fallback(url: str) -> QLabel:
    label = QLabel(
        "<h2>Calendar widget unavailable</h2>"
        "<p style='color:#666;'>QWebEngineView could not be loaded.</p>"
        f'<p><a href="{url}">Open Investing.com Economic Calendar in browser</a></p>'
    )
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setOpenExternalLinks(True)
    return label


class MyCalendarView(BaseView):
    """Personal FRED-backed calendar. Real implementation lands in v0.7."""

    view_name = "My Calendar"

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(
            _make_placeholder(
                "My Calendar",
                "Your curated release calendar. Coming in v0.7 — needs FRED client (v0.3) "
                "and catalog (v0.6) to land first.",
            )
        )
        self.sidebar_widget = QLabel("My Calendar filters\n(coming in v0.7)")


class ExplorerView(BaseView):
    view_name = "Explorer"

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_make_placeholder("Explorer view", "Coming in v0.5"))
        self.sidebar_widget = QLabel("Explorer navigation\n(placeholder)")


class SeriesDetailView(BaseView):
    view_name = "Series Detail"

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_make_placeholder("Series Detail view", "Coming in v0.4"))
        self.sidebar_widget = QLabel("Series navigation\n(placeholder)")


class CoreIndicatorsView(BaseView):
    view_name = "Core Indicators"

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(_make_placeholder("Core Indicators view", "Coming in v0.6"))
        self.sidebar_widget = QLabel("Market filters\n(placeholder)")


class MarketCalendarView(BaseView):
    """Market Calendar — embeds Investing.com Economic Calendar widget."""

    view_name = "Market Calendar"

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtWebEngineWidgets import QWebEngineView

            self._web_view: QWidget = QWebEngineView()
            self._web_view.setFixedWidth(720)
            self._web_view.setUrl(QUrl(INVESTING_COM_CALENDAR_URL))

            container = QWidget()
            hbox = QHBoxLayout(container)
            hbox.setContentsMargins(0, 0, 0, 0)
            hbox.addStretch(1)
            hbox.addWidget(self._web_view)
            hbox.addStretch(1)

            layout.addWidget(container)
        except ImportError:
            self._web_view = _make_fallback(INVESTING_COM_CALENDAR_URL)
            layout.addWidget(self._web_view)

        self.sidebar_widget = QLabel("Market Calendar filters\n(coming in Issues #22-#24)")
