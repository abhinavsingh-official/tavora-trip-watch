"""Thin client for Sabre Dev Studio.

Auth is double-base64 client-credentials. Tokens last 7 days, so we cache
one in memory instead of fetching a new one per price check.
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
"""Prevents a thundering herd on refresh - without the lock, a bunch of
concurrent requests hitting an expired token at once would all fire off
their own token request at the same time.
"""
_token_lock = threading.Lock()

"""Same idea as the cache in hotelbeds_client.py - absorbs rapid repeats
without changing how often we actually hit Sabre for a fresh price.
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
        """Re-check after acquiring the lock - another thread may have beaten us to it."""
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
        """Refresh an hour early instead of cutting it right at expiry."""
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
