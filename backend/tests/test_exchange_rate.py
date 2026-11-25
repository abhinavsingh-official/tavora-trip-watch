"""Known-issue fix: EUR->INR used to be one fixed number in the code. Now it's a live rate from a
free FX API, cached for a while, with a fallback if that API is ever unreachable. These tests don't
use the `stable_exchange_rate` autouse fixture's monkeypatch - they exercise exchange_rate.py itself."""

import httpx
import pytest

from app import exchange_rate, ttl_cache


@pytest.fixture(autouse=True)
def stable_exchange_rate():
    """Overrides conftest's autouse fixture of the same name - this file tests the real function."""
    yield


@pytest.fixture(autouse=True)
def _isolated_cache():
    # The module-level ttl_cache is shared state; don't let one test's cached rate leak into another
    ttl_cache.clear()
    yield
    ttl_cache.clear()


def test_uses_the_live_rate_when_the_api_responds(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"rates": {"INR": 101.5}}

    monkeypatch.setattr(httpx, "get", lambda *a, **k: FakeResponse())
    assert exchange_rate.get_eur_to_inr_rate() == 101.5


def test_falls_back_to_the_fixed_rate_if_the_api_is_unreachable(monkeypatch):
    def _raise(*args, **kwargs):
        raise httpx.ConnectError("no network")

    monkeypatch.setattr(httpx, "get", _raise)
    assert exchange_rate.get_eur_to_inr_rate() == exchange_rate.FALLBACK_EUR_TO_INR_RATE


def test_caches_the_rate_instead_of_calling_the_api_every_time(monkeypatch):
    calls = {"count": 0}

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"rates": {"INR": 99.0}}

    def _get(*args, **kwargs):
        calls["count"] += 1
        return FakeResponse()

    monkeypatch.setattr(httpx, "get", _get)
    exchange_rate.get_eur_to_inr_rate()
    exchange_rate.get_eur_to_inr_rate()
    assert calls["count"] == 1
