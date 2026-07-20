"""Smoke tests for the econ_app package.

These verify the package is installed and importable. Real tests come with
subsequent issues as functionality is added.
"""

from __future__ import annotations


def test_package_imports() -> None:
    """The package can be imported without error."""
    import econ_app

    assert econ_app.__version__ == "0.1.0"


def test_main_returns_zero() -> None:
    """The main() function runs cleanly and returns 0."""
    from econ_app.__main__ import main

    assert main() == 0
