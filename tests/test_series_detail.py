"""Tests for Series Detail view.

Uses a mocked AppCache so tests don't hit the real FRED API or SQLite.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import MagicMock, patch

import pytest

from econ_app.services.models import Observation, SeriesMetadata


@pytest.fixture()
def sample_metadata() -> SeriesMetadata:
    return SeriesMetadata(
        id="CPIAUCSL",
        title="Consumer Price Index for All Urban Consumers: All Items",
        notes="A note from the Bureau of Labor Statistics.",
        frequency="Monthly",
        frequency_short="M",
        units="Index 1982-1984=100",
        units_short="Index",
        seasonal_adjustment="Seasonally Adjusted",
        seasonal_adjustment_short="SA",
        observation_start=date(2020, 1, 1),
        observation_end=date(2024, 5, 1),
        last_updated=datetime(2024, 6, 12, 7, 41, 3, tzinfo=UTC),
        popularity=94,
    )


@pytest.fixture()
def sample_observations() -> list[Observation]:
    return [
        Observation(date=date(2024, 1, 1), value=308.417, is_missing=False),
        Observation(date=date(2024, 2, 1), value=310.326, is_missing=False),
        Observation(date=date(2024, 3, 1), value=312.230, is_missing=False),
    ]


def test_series_detail_view_creates(qtbot) -> None:
    """SeriesDetailView instantiates without loading data."""
    from econ_app.ui.views.series_detail import SeriesDetailView

    view = SeriesDetailView()
    qtbot.addWidget(view)

    assert view.view_name == "Series Detail"
    assert view._loaded is False


def test_load_series_populates_metadata(qtbot, sample_metadata, sample_observations) -> None:
    """load_series() sets title, metadata line, and attribution."""
    from econ_app.ui.views.series_detail import SeriesDetailView

    mock_cache = MagicMock()
    mock_cache.get_metadata.return_value = sample_metadata
    mock_cache.get_observations.return_value = sample_observations
    mock_cache.get_last_synced.return_value = datetime.now(UTC)

    with patch("econ_app.ui.views.series_detail.get_app_cache", return_value=mock_cache):
        view = SeriesDetailView()
        qtbot.addWidget(view)
        view.load_series("CPIAUCSL")

    assert "Consumer Price Index" in view._title_label.text()
    assert "Monthly" in view._meta_label.text()
    assert "Bureau of Labor Statistics" in view._attribution_label.text()
    assert "CPIAUCSL" in view._attribution_label.text()
    assert view._loaded is True


def test_load_series_handles_fred_error(qtbot) -> None:
    """FRED errors show error state in the chart, don't crash."""
    from econ_app.services.fred_client import FREDNotFoundError
    from econ_app.ui.views.series_detail import SeriesDetailView

    mock_cache = MagicMock()
    mock_cache.get_metadata.side_effect = FREDNotFoundError("Series not found")

    with patch("econ_app.ui.views.series_detail.get_app_cache", return_value=mock_cache):
        view = SeriesDetailView()
        qtbot.addWidget(view)
        view.load_series("NONEXISTENT")

    assert "Could not load" in view._title_label.text()
    assert view._loaded is False


def test_load_series_handles_missing_api_key(qtbot) -> None:
    """No FRED key shows configuration error, doesn't crash."""
    from econ_app.ui.views.series_detail import SeriesDetailView

    with patch(
        "econ_app.ui.views.series_detail.get_app_cache",
        side_effect=RuntimeError("No FRED API key configured."),
    ):
        view = SeriesDetailView()
        qtbot.addWidget(view)
        view.load_series("CPIAUCSL")

    assert "Configuration needed" in view._title_label.text()
