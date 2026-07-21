"""FRED API client.

Wraps httpx for all FRED interactions. Handles:
- Authentication (API key in query params)
- Standard error mapping (network, 404, 429, invalid key)
- Rate limit backoff with one retry
- Response parsing to typed dataclasses

Per ADR-0002 Musts 7.1, 7.9.
Per Issues #28, #29, #30, #32.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from econ_app.services.models import Observation, SeriesMetadata

log = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.stlouisfed.org/fred"
DEFAULT_TIMEOUT_SEC = 30.0
MAX_BACKOFF_SEC = 60.0
USER_AGENT = "Econ-App/0.1.0 (personal desktop app; +https://github.com/Careycarroll/Econ-App)"


class FREDAPIError(Exception):
    """Base exception for all FRED API failures."""


class FREDNetworkError(FREDAPIError):
    """Network-level failure (timeout, DNS, connection refused)."""


class FREDInvalidKeyError(FREDAPIError):
    """API key was rejected by FRED (HTTP 400 with key-related message)."""


class FREDNotFoundError(FREDAPIError):
    """Series or resource not found (HTTP 404)."""


class FREDRateLimitError(FREDAPIError):
    """Rate limit exceeded, even after one retry (HTTP 429)."""


class FREDClient:
    """Client for the FRED API.

    Usage:
        client = FREDClient(api_key)
        metadata = client.get_series_metadata("CPIAUCSL")
        observations = client.get_observations("CPIAUCSL")
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT_SEC,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": USER_AGENT},
        )

    def close(self) -> None:
        """Close the underlying HTTP client. Call when done."""
        self._client.close()

    def __enter__(self) -> FREDClient:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def get_series_metadata(self, series_id: str) -> SeriesMetadata:
        """Fetch metadata for a single series from /fred/series.

        Raises:
            FREDNotFoundError: if the series ID doesn't exist
            FREDInvalidKeyError: if the API key is rejected
            FREDRateLimitError: if rate-limited even after retry
            FREDNetworkError: on network failure
            FREDAPIError: for other API errors
        """
        data = self._get("series", {"series_id": series_id})
        seriess = data.get("seriess", [])
        if not seriess:
            raise FREDNotFoundError(f"Series not found: {series_id}")
        return SeriesMetadata.from_fred(seriess[0])

    def get_observations(
        self,
        series_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[Observation]:
        """Fetch observations for a series from /fred/series/observations.

        Args:
            series_id: FRED series ID (e.g., "CPIAUCSL")
            start_date: ISO date string, e.g., "1990-01-01" (optional)
            end_date: ISO date string (optional)

        Raises:
            Same as get_series_metadata.
        """
        params: dict[str, str] = {"series_id": series_id}
        if start_date:
            params["observation_start"] = start_date
        if end_date:
            params["observation_end"] = end_date

        data = self._get("series/observations", params)
        return [Observation.from_fred(o) for o in data.get("observations", [])]

    # -------------------------------------------------------------- internal

    def _get(self, endpoint: str, params: dict[str, str]) -> dict[str, Any]:
        """Perform a GET request with API key + JSON format, mapping errors."""
        url = f"{self._base_url}/{endpoint}"
        full_params = {**params, "api_key": self._api_key, "file_type": "json"}

        try:
            response = self._client.get(url, params=full_params)
        except httpx.RequestError as e:
            raise FREDNetworkError(f"Network error calling FRED: {e}") from e

        # Handle rate limiting with one retry
        if response.status_code == 429:
            retry_after = _parse_retry_after(response.headers.get("Retry-After"))
            log.warning("FRED rate limit hit; sleeping %.1fs before retry", retry_after)
            time.sleep(retry_after)
            try:
                response = self._client.get(url, params=full_params)
            except httpx.RequestError as e:
                raise FREDNetworkError(f"Network error on retry: {e}") from e
            if response.status_code == 429:
                raise FREDRateLimitError(
                    "FRED rate limit exceeded even after backoff. Try again in a moment."
                )

        return _handle_response(response)


def _parse_retry_after(header: str | None) -> float:
    """Parse Retry-After header, capped at MAX_BACKOFF_SEC. Default to 5s if unparseable."""
    if not header:
        return 5.0
    try:
        secs = float(header)
    except ValueError:
        return 5.0
    return min(max(secs, 1.0), MAX_BACKOFF_SEC)


def _handle_response(response: httpx.Response) -> dict[str, Any]:
    """Map HTTP status to typed exceptions and return parsed JSON on success."""
    if response.status_code == 200:
        return response.json()

    if response.status_code == 404:
        raise FREDNotFoundError("Resource not found")

    if response.status_code == 400:
        # FRED returns 400 for various reasons; check message for key issues
        try:
            body = response.json()
            msg = body.get("error_message", "").lower()
        except Exception:
            msg = ""
        if "api_key" in msg or "key" in msg:
            raise FREDInvalidKeyError(f"FRED rejected the API key: {msg}")
        raise FREDAPIError(f"FRED API error (400): {msg or 'unknown'}")

    if response.status_code == 429:
        raise FREDRateLimitError("Rate limit exceeded")

    raise FREDAPIError(f"FRED API error (HTTP {response.status_code})")
