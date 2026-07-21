"""Tests for src/econ_app/config.py."""

from __future__ import annotations


def test_get_fred_api_key_missing(monkeypatch) -> None:
    """Returns None when FRED_API_KEY is unset."""
    from econ_app.config import get_fred_api_key

    monkeypatch.delenv("FRED_API_KEY", raising=False)
    assert get_fred_api_key() is None


def test_get_fred_api_key_empty(monkeypatch) -> None:
    """Returns None when FRED_API_KEY is empty or whitespace."""
    from econ_app.config import get_fred_api_key

    monkeypatch.setenv("FRED_API_KEY", "")
    assert get_fred_api_key() is None

    monkeypatch.setenv("FRED_API_KEY", "   ")
    assert get_fred_api_key() is None


def test_get_fred_api_key_malformed(monkeypatch, caplog) -> None:
    """Returns None and logs warning when key is not 32 hex chars."""
    from econ_app.config import get_fred_api_key

    monkeypatch.setenv("FRED_API_KEY", "not-a-real-key")
    result = get_fred_api_key()
    assert result is None
    assert any("does not match expected format" in rec.message for rec in caplog.records)


def test_get_fred_api_key_valid(monkeypatch) -> None:
    """Returns the key when format is valid."""
    from econ_app.config import get_fred_api_key

    valid_key = "abcdef0123456789abcdef0123456789"
    monkeypatch.setenv("FRED_API_KEY", valid_key)
    assert get_fred_api_key() == valid_key
