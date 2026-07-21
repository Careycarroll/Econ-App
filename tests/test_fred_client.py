"""Tests for the FRED API client.

Uses respx to mock HTTP responses so tests are offline, deterministic, and fast.
"""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from econ_app.services.fred_client import (
    FREDAPIError,
    FREDClient,
    FREDInvalidKeyError,
    FREDNetworkError,
    FREDNotFoundError,
    FREDRateLimitError,
)

FIXTURES = Path(__file__).parent / "fixtures"
BASE_URL = "https://api.stlouisfed.org/fred"


def _load_fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture()
def client() -> FREDClient:
    """A FREDClient with a well-formed dummy API key."""
    c = FREDClient(api_key="a" * 32)
    yield c
    c.close()


# -------------------------------------------------------------- metadata


@respx.mock
def test_get_series_metadata_success(client: FREDClient) -> None:
    """Successful /series response is parsed into SeriesMetadata."""
    respx.get(f"{BASE_URL}/series").mock(
        return_value=httpx.Response(200, json=_load_fixture("fred_series_cpiaucsl.json"))
    )

    metadata = client.get_series_metadata("CPIAUCSL")
    assert metadata.id == "CPIAUCSL"
    assert "Consumer Price Index" in metadata.title
    assert metadata.frequency == "Monthly"
    assert metadata.units_short == "Index 1982-1984=100"
    assert metadata.popularity == 94


@respx.mock
def test_get_series_metadata_not_found(client: FREDClient) -> None:
    """404 response raises FREDNotFoundError."""
    respx.get(f"{BASE_URL}/series").mock(return_value=httpx.Response(404))

    with pytest.raises(FREDNotFoundError):
        client.get_series_metadata("NONEXISTENT")


@respx.mock
def test_get_series_metadata_empty_result(client: FREDClient) -> None:
    """200 with empty seriess[] raises FREDNotFoundError."""
    respx.get(f"{BASE_URL}/series").mock(return_value=httpx.Response(200, json={"seriess": []}))

    with pytest.raises(FREDNotFoundError):
        client.get_series_metadata("EMPTY")


# -------------------------------------------------------------- observations


@respx.mock
def test_get_observations_success(client: FREDClient) -> None:
    """Observations parse correctly, including missing values."""
    respx.get(f"{BASE_URL}/series/observations").mock(
        return_value=httpx.Response(200, json=_load_fixture("fred_observations_cpiaucsl.json"))
    )

    obs = client.get_observations("CPIAUCSL")
    assert len(obs) == 5
    assert obs[0].value == pytest.approx(308.417)
    assert obs[0].is_missing is False
    # Last observation is a missing value (".") in the fixture
    assert obs[-1].value is None
    assert obs[-1].is_missing is True


@respx.mock
def test_get_observations_with_date_range(client: FREDClient) -> None:
    """Date range params are passed through to the request."""
    route = respx.get(f"{BASE_URL}/series/observations").mock(
        return_value=httpx.Response(200, json={"observations": []})
    )

    client.get_observations("CPIAUCSL", start_date="2020-01-01", end_date="2020-12-31")

    assert route.called
    req = route.calls.last.request
    assert "observation_start=2020-01-01" in str(req.url)
    assert "observation_end=2020-12-31" in str(req.url)


# ---------------------------------------------------------------- errors


@respx.mock
def test_invalid_api_key(client: FREDClient) -> None:
    """400 with 'api_key' in error message raises FREDInvalidKeyError."""
    respx.get(f"{BASE_URL}/series").mock(
        return_value=httpx.Response(
            400,
            json={"error_message": "Bad request. Variable api_key is not registered."},
        )
    )

    with pytest.raises(FREDInvalidKeyError):
        client.get_series_metadata("CPIAUCSL")


@respx.mock
def test_generic_400_error(client: FREDClient) -> None:
    """400 without key-related message raises generic FREDAPIError."""
    respx.get(f"{BASE_URL}/series").mock(
        return_value=httpx.Response(400, json={"error_message": "Bad parameter"})
    )

    with pytest.raises(FREDAPIError):
        client.get_series_metadata("CPIAUCSL")


@respx.mock
def test_network_error_raises_network_error(client: FREDClient) -> None:
    """httpx transport errors are wrapped as FREDNetworkError."""
    respx.get(f"{BASE_URL}/series").mock(side_effect=httpx.ConnectError("connection refused"))

    with pytest.raises(FREDNetworkError):
        client.get_series_metadata("CPIAUCSL")


# ---------------------------------------------------------------- rate limit


@respx.mock
def test_rate_limit_retries_and_succeeds(client: FREDClient, monkeypatch) -> None:
    """429 followed by 200 succeeds after backoff."""
    # Speed up test by patching sleep to no-op
    monkeypatch.setattr("time.sleep", lambda _: None)

    route = respx.get(f"{BASE_URL}/series").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "1"}),
            httpx.Response(200, json=_load_fixture("fred_series_cpiaucsl.json")),
        ]
    )

    metadata = client.get_series_metadata("CPIAUCSL")
    assert metadata.id == "CPIAUCSL"
    assert route.call_count == 2


@respx.mock
def test_rate_limit_persistent_raises(client: FREDClient, monkeypatch) -> None:
    """Two consecutive 429s raise FREDRateLimitError."""
    monkeypatch.setattr("time.sleep", lambda _: None)

    respx.get(f"{BASE_URL}/series").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "1"}),
            httpx.Response(429, headers={"Retry-After": "1"}),
        ]
    )

    with pytest.raises(FREDRateLimitError):
        client.get_series_metadata("CPIAUCSL")
