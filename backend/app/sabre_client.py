"""Thin client for Sabre Dev Studio (confirmed working, docs/NOTES.md round 9).

Auth: double-base64 client-credentials scheme. The issued token is valid for
7 days, so it's cached in memory for its lifetime rather than re-fetched on
every price check - there's no reason to burn a fresh token per request.
"""

import base64
import threading
import time

import httpx

from app import ttl_cache
from app.config import get_settings

settings = get_settings()

_cached_token: str | None = None
_cached_token_expires_at: float = 0.0
"""Guards against a thundering-herd token refresh: without this, many
concurrent requests hitting an expired token at once (exactly what Sec. 12's
100-request load test would produce) could each independently fire a token
request simultaneously, racing to write _cached_token.
"""
_token_lock = threading.Lock()

"""Same reasoning as hotelbeds_client.py's cache - absorbs rapid repeats
without changing the real "how often do we get a fresh price" cadence.
"""
_CACHE_TTL_SECONDS = 240


def _build_auth_header() -> str:
    step1 = base64.b64encode(settings.sabre_user_id.encode()).decode()
    step2 = base64.b64encode(settings.sabre_password.encode()).decode()
    combined = f"{step1}:{step2}"
    return base64.b64encode(combined.encode()).decode()


def get_token() -> str:
    global _cached_token, _cached_token_expires_at

    if _cached_token and time.time() < _cached_token_expires_at:
        return _cached_token

    with _token_lock:
        """Re-check after acquiring the lock - another thread may have already
        refreshed it while this one was waiting.
        """
        if _cached_token and time.time() < _cached_token_expires_at:
            return _cached_token

        response = httpx.post(
            settings.sabre_token_url,
            data={"grant_type": "client_credentials"},
            headers={
                "Authorization": f"Basic {_build_auth_header()}",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            timeout=20.0,
        )
        response.raise_for_status()
        body = response.json()

        _cached_token = body["access_token"]
        """Refresh a little before actual expiry, not at the exact edge."""
        _cached_token_expires_at = time.time() + body["expires_in"] - 3600
        return _cached_token


def search_flights(origin: str, destination: str, departure_date: str, adults: int) -> dict:
    """One-way Bargain Finder Max v4 search. Call twice (outbound + return legs)."""
    cache_key = f"sabre:{origin}:{destination}:{departure_date}:{adults}"
    cached = ttl_cache.get(cache_key, _CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    token = get_token()

    payload = {
        "OTA_AirLowFareSearchRQ": {
            "Version": "4",
            "POS": {
                "Source": [
                    {
                        "PseudoCityCode": settings.sabre_pcc,
                        "RequestorID": {
                            "Type": "1",
                            "ID": "1",
                            "CompanyName": {"Code": "TN"},
                        },
                    }
                ]
            },
            "OriginDestinationInformation": [
                {
                    "RPH": "1",
                    "DepartureDateTime": f"{departure_date}T00:00:00",
                    "OriginLocation": {"LocationCode": origin},
                    "DestinationLocation": {"LocationCode": destination},
                }
            ],
            "TravelPreferences": {"ValidInterlineTicket": True},
            "TravelerInfoSummary": {
                "AirTravelerAvail": [
                    {"PassengerTypeQuantity": [{"Code": "ADT", "Quantity": adults}]}
                ],
                "SeatsRequested": [adults],
            },
            "TPA_Extensions": {
                "IntelliSellTransaction": {"RequestType": {"Name": "50ITINS"}}
            },
        }
    }

    response = httpx.post(
        f"{settings.sabre_base_url}/v4/offers/shop",
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )
    response.raise_for_status()
    result = response.json()
    ttl_cache.set(cache_key, result)
    return result
