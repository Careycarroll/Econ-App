"""Time-series transforms.

Per ADR-0005, raw values are stored; transforms compute on read. This module
provides pandas-backed transform functions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import pandas as pd

from econ_app.services.models import Observation, SeriesMetadata

log = logging.getLogger(__name__)

TRANSFORM_LEVEL = "level"
TRANSFORM_YOY = "yoy_pct"
TRANSFORM_MOM = "mom_pct"
TRANSFORM_QOQ = "qoq_pct"
TRANSFORM_ANNUALIZED = "annualized"


@dataclass(frozen=True)
class TransformOption:
    key: str
    label: str
    y_axis_label: str


TRANSFORMS: list[TransformOption] = [
    TransformOption(TRANSFORM_LEVEL, "Level", ""),
    TransformOption(TRANSFORM_YOY, "YoY %", "YoY %"),
    TransformOption(TRANSFORM_MOM, "MoM %", "MoM %"),
    TransformOption(TRANSFORM_QOQ, "QoQ %", "QoQ %"),
    TransformOption(TRANSFORM_ANNUALIZED, "Annualized %", "Annualized %"),
]


def apply_transform(
    observations: list[Observation],
    transform_key: str,
    frequency_short: str = "",
) -> list[Observation]:
    """Return a new list of observations with the requested transform applied."""
    if not observations or transform_key == TRANSFORM_LEVEL:
        return observations

    df = pd.DataFrame(
        {
            "date": [o.date for o in observations],
            "value": [o.value for o in observations],
        }
    )
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date").sort_index()

    if transform_key == TRANSFORM_YOY:
        periods = _yoy_periods(frequency_short)
        result = df["value"].pct_change(periods=periods) * 100
    elif transform_key == TRANSFORM_MOM:
        if frequency_short not in ("M", "SM", "BW", "W", "D"):
            log.warning("MoM on non-monthly (freq=%s)", frequency_short)
        result = df["value"].pct_change(periods=1) * 100
    elif transform_key == TRANSFORM_QOQ:
        if frequency_short not in ("Q", "M"):
            log.warning("QoQ on non-quarterly (freq=%s)", frequency_short)
        periods = 1 if frequency_short == "Q" else 3
        result = df["value"].pct_change(periods=periods) * 100
    elif transform_key == TRANSFORM_ANNUALIZED:
        if frequency_short == "M":
            mom = df["value"].pct_change(periods=1)
            result = ((1 + mom) ** 12 - 1) * 100
        elif frequency_short == "Q":
            qoq = df["value"].pct_change(periods=1)
            result = ((1 + qoq) ** 4 - 1) * 100
        else:
            log.warning("Annualized on non-M/Q (freq=%s)", frequency_short)
            result = df["value"]
    else:
        log.warning("Unknown transform key: %s", transform_key)
        return observations

    out: list[Observation] = []
    for dt, val in result.items():
        py_date = dt.date() if hasattr(dt, "date") else dt
        if pd.isna(val):
            out.append(Observation(date=py_date, value=None, is_missing=True))
        else:
            out.append(Observation(date=py_date, value=float(val), is_missing=False))
    return out


def is_applicable(transform_key: str, metadata: SeriesMetadata) -> bool:
    """Return True if the transform is meaningful for this series' frequency."""
    freq = metadata.frequency_short or ""
    if transform_key == TRANSFORM_LEVEL:
        return True
    if transform_key == TRANSFORM_YOY:
        return freq in ("M", "Q", "SA", "A", "W", "D")
    if transform_key == TRANSFORM_MOM:
        return freq == "M"
    if transform_key == TRANSFORM_QOQ:
        return freq in ("M", "Q")
    if transform_key == TRANSFORM_ANNUALIZED:
        return freq in ("M", "Q")
    return False


def _yoy_periods(frequency_short: str) -> int:
    return {"D": 365, "W": 52, "M": 12, "Q": 4, "SA": 2, "A": 1}.get(frequency_short, 12)
