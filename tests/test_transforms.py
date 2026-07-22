"""Tests for the transforms module."""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from econ_app.services.models import Observation, SeriesMetadata
from econ_app.services.transforms import (
    TRANSFORM_ANNUALIZED,
    TRANSFORM_LEVEL,
    TRANSFORM_MOM,
    TRANSFORM_YOY,
    apply_transform,
    is_applicable,
)


def _obs(y: int, m: int, v: float | None) -> Observation:
    return Observation(date=date(y, m, 1), value=v, is_missing=v is None)


@pytest.fixture()
def monthly_metadata() -> SeriesMetadata:
    return SeriesMetadata(
        id="TEST_M",
        title="Monthly test series",
        notes=None,
        frequency="Monthly",
        frequency_short="M",
        units="Index",
        units_short="Idx",
        seasonal_adjustment="SA",
        seasonal_adjustment_short="SA",
        observation_start=date(2020, 1, 1),
        observation_end=date(2024, 12, 1),
        last_updated=datetime(2024, 12, 1, tzinfo=UTC),
        popularity=50,
    )


def test_level_transform_returns_input_unchanged() -> None:
    obs = [_obs(2024, 1, 100.0), _obs(2024, 2, 101.0)]
    result = apply_transform(obs, TRANSFORM_LEVEL, frequency_short="M")
    assert result == obs


def test_yoy_transform_monthly() -> None:
    obs = [_obs(2023 + (m - 1) // 12, ((m - 1) % 12) + 1, 100.0 + m) for m in range(1, 25)]
    result = apply_transform(obs, TRANSFORM_YOY, frequency_short="M")
    assert all(r.is_missing for r in result[:12])
    assert result[12].value == pytest.approx((113 - 101) / 101 * 100, rel=1e-3)


def test_mom_transform() -> None:
    obs = [_obs(2024, 1, 100.0), _obs(2024, 2, 105.0), _obs(2024, 3, 110.25)]
    result = apply_transform(obs, TRANSFORM_MOM, frequency_short="M")
    assert result[0].is_missing
    assert result[1].value == pytest.approx(5.0)
    assert result[2].value == pytest.approx(5.0)


def test_annualized_transform() -> None:
    obs = [_obs(2024, 1, 100.0), _obs(2024, 2, 101.0)]
    result = apply_transform(obs, TRANSFORM_ANNUALIZED, frequency_short="M")
    assert result[1].value == pytest.approx(((1.01) ** 12 - 1) * 100, rel=1e-3)


def test_transform_preserves_missing_values() -> None:
    obs = [_obs(2024, 1, 100.0), _obs(2024, 2, None), _obs(2024, 3, 110.0)]
    result = apply_transform(obs, TRANSFORM_MOM, frequency_short="M")
    assert result[1].is_missing
    assert result[2].is_missing


def test_is_applicable_mom_only_monthly(monthly_metadata: SeriesMetadata) -> None:
    assert is_applicable(TRANSFORM_MOM, monthly_metadata) is True
    q_meta = SeriesMetadata(**{**monthly_metadata.__dict__, "frequency_short": "Q"})
    assert is_applicable(TRANSFORM_MOM, q_meta) is False


def test_is_applicable_annualized_monthly_and_quarterly(monthly_metadata: SeriesMetadata) -> None:
    assert is_applicable(TRANSFORM_ANNUALIZED, monthly_metadata) is True
    q_meta = SeriesMetadata(**{**monthly_metadata.__dict__, "frequency_short": "Q"})
    assert is_applicable(TRANSFORM_ANNUALIZED, q_meta) is True
    a_meta = SeriesMetadata(**{**monthly_metadata.__dict__, "frequency_short": "A"})
    assert is_applicable(TRANSFORM_ANNUALIZED, a_meta) is False
