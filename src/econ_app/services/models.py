"""Data model classes for FRED API responses.

Plain dataclasses — no persistence layer coupling. The cache layer (Issue #31)
translates between these and SQL rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True)
class Observation:
    """A single time-series observation."""

    date: date
    value: float | None
    is_missing: bool

    @classmethod
    def from_fred(cls, raw: dict) -> Observation:
        """Build from a FRED /observations response row.

        FRED encodes missing values as the string ".".
        """
        raw_value = raw["value"]
        if raw_value == ".":
            return cls(
                date=date.fromisoformat(raw["date"]),
                value=None,
                is_missing=True,
            )
        return cls(
            date=date.fromisoformat(raw["date"]),
            value=float(raw_value),
            is_missing=False,
        )


@dataclass(frozen=True)
class SeriesMetadata:
    """Metadata for a single FRED series (from /series endpoint)."""

    id: str
    title: str
    notes: str | None
    frequency: str
    frequency_short: str
    units: str
    units_short: str
    seasonal_adjustment: str
    seasonal_adjustment_short: str
    observation_start: date
    observation_end: date
    last_updated: datetime
    popularity: int

    @classmethod
    def from_fred(cls, raw: dict) -> SeriesMetadata:
        """Build from a FRED /series response row."""
        return cls(
            id=raw["id"],
            title=raw["title"],
            notes=raw.get("notes"),
            frequency=raw["frequency"],
            frequency_short=raw["frequency_short"],
            units=raw["units"],
            units_short=raw["units_short"],
            seasonal_adjustment=raw["seasonal_adjustment"],
            seasonal_adjustment_short=raw["seasonal_adjustment_short"],
            observation_start=date.fromisoformat(raw["observation_start"]),
            observation_end=date.fromisoformat(raw["observation_end"]),
            last_updated=_parse_fred_datetime(raw["last_updated"]),
            popularity=raw["popularity"],
        )


def _parse_fred_datetime(s: str) -> datetime:
    """Parse FRED's last_updated timestamps.

    Format examples: '2024-06-12 07:41:03-05', '2024-06-12 07:41:03-06'.
    FRED uses non-standard timezone format (missing minutes), so we pad it.
    """
    # FRED format: 'YYYY-MM-DD HH:MM:SS[+-]TZ' where TZ is hours only
    # Normalize to ISO 8601: 'YYYY-MM-DDTHH:MM:SS[+-]TZ:00'
    parts = s.rsplit(" ", 1)  # split date part from time part
    if len(parts) == 2:
        date_str, time_str = parts
        # Pad timezone if it's just hours (e.g., "-05" -> "-05:00")
        if len(time_str) >= 3 and time_str[-3] in ("+", "-"):
            time_str = time_str + ":00"
        return datetime.fromisoformat(f"{date_str}T{time_str}")
    return datetime.fromisoformat(s)
