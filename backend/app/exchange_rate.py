"""Live EUR->INR conversion, replacing the old single fixed rate. Hotelbeds prices arrive in EUR;
this calls a free, keyless FX API (Frankfurter, backed by the European Central Bank's daily rates)
for the real current rate, cached for an hour since FX moves far too slowly to justify a live call
on every price check. Falls back to a fixed, clearly-labelled rate if the API is ever unreachable,
so a flaky third-party FX provider can't take hotel pricing down with it."""

import logging

import httpx

from app import ttl_cache

logger = logging.getLogger(__name__)

# Last known-good rate, used only if the live lookup fails - not treated as "the" rate anymore.
FALLBACK_EUR_TO_INR_RATE = 95.0

_CACHE_KEY = "eur_to_inr_rate"
_CACHE_TTL_SECONDS = 3600
_TIMEOUT_SECONDS = 3.0
_API_URL = "https://api.frankfurter.dev/v1/latest?base=EUR&symbols=INR"


def get_eur_to_inr_rate() -> float:
    cached = ttl_cache.get(_CACHE_KEY, _CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    try:
        response = httpx.get(_API_URL, timeout=_TIMEOUT_SECONDS)
        response.raise_for_status()
        rate = float(response.json()["rates"]["INR"])
    except Exception:
        logger.warning("Live EUR->INR lookup failed, using the fixed fallback rate", exc_info=True)
        return FALLBACK_EUR_TO_INR_RATE

    ttl_cache.set(_CACHE_KEY, rate)
    return rate
