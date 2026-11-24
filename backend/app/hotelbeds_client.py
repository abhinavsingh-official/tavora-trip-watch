"""Thin client for Hotelbeds Apitude.

Auth is a per-request signature, SHA256(apikey + secret + unix_timestamp),
so unlike Sabre's token it can't be cached - has to be recomputed every call.

Hotelbeds' own destination codes are misleading ("GOA" is Genoa, not Goa;
Goa itself is "GOI"), so we search by geolocation instead and hardcode
coordinates for known destinations below. That also avoids burning the
free key's 50/day quota on content-API lookups just to resolve a code.
"""

import hashlib
import time

import httpx

from app import rate_limit, ttl_cache
from app.config import get_settings

settings = get_settings()

"""Hotelbeds' burst limit is 8 requests per 4 seconds. Stay under it -
if we get throttled it just looks like "no hotels found" downstream.
"""
_MIN_CALL_INTERVAL_SECONDS = 0.6

"""Absorbs rapid repeats (double clicks, a page re-fetching on mount)
without changing how often we actually hit Hotelbeds for a fresh price.
"""
_CACHE_TTL_SECONDS = 240

# (latitude, longitude) for destinations we support
DESTINATION_COORDINATES = {
    "GOA": (15.2993, 74.1240),
    "JAIPUR": (26.9124, 75.7873),
}


def _sign(api_key: str, secret: str) -> str:
    timestamp = str(int(time.time()))
    raw = f"{api_key}{secret}{timestamp}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _headers(api_key: str, secret: str) -> dict:
    return {
        "Api-key": api_key,
        "X-Signature": _sign(api_key, secret),
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def search_hotels(
    destination: str,
    check_in: str,
    check_out: str,
    rooms: int,
    adults: int,
    *,
    api_key: str | None = None,
    secret: str | None = None,
    radius_km: int = 30,
) -> dict:
    """
    api_key/secret default to the primary account's credentials. The seed
    script (fetch_hotel_directory.py) passes the fallback account's
    credentials explicitly for its one-time bulk fetch, and widens
    radius_km beyond the default 30 to pull more hotels per destination.
    """
    coordinates = DESTINATION_COORDINATES.get(destination.upper())
    if coordinates is None:
        raise ValueError(
            f"No known coordinates for destination '{destination}' - "
            "add it to DESTINATION_COORDINATES after confirming it via a real "
            "geolocation search, not a guessed destination code."
        )
    latitude, longitude = coordinates

    resolved_api_key = api_key or settings.hotelbeds_hotel_api_key
    resolved_secret = secret or settings.hotelbeds_hotel_secret

    cache_key = (
        f"hotelbeds:{destination.upper()}:{check_in}:{check_out}:{rooms}:{adults}:{radius_km}"
    )
    cached = ttl_cache.get(cache_key, _CACHE_TTL_SECONDS)
    if cached is not None:
        return cached

    """
    Hotelbeds wants one occupancies entry per room, not one combined entry
    with "rooms" as a multiplier - {"rooms": 2, "adults": 4} as a single
    entry is malformed and most hotels won't price it (we saw 5 results for
    Goa that way vs 47 once split properly). Split adults evenly per room.

    If rooms > adults (more rooms requested than people to put in them),
    splitting evenly would give some rooms 0 adults - Hotelbeds rejects
    that outright with a 400, confirmed live. A room with nobody in it
    isn't a real booking anyway, so cap the number of occupied rooms
    actually sent at the real adult count.
    """
    effective_rooms = min(rooms, adults)
    base_adults_per_room, remainder = divmod(adults, effective_rooms)
    occupancies = [
        {
            "rooms": 1,
            "adults": base_adults_per_room + (1 if i < remainder else 0),
            "children": 0,
        }
        for i in range(effective_rooms)
    ]

    payload = {
        "stay": {"checkIn": check_in, "checkOut": check_out},
        "occupancies": occupancies,
        "geolocation": {
            "latitude": latitude,
            "longitude": longitude,
            "radius": radius_km,
            "unit": "km",
        },
    }

    rate_limit.throttle("hotelbeds", _MIN_CALL_INTERVAL_SECONDS)
    response = httpx.post(
        f"{settings.hotelbeds_base_url}/hotel-api/1.0/hotels",
        json=payload,
        headers=_headers(resolved_api_key, resolved_secret),
        timeout=30.0,
    )
    response.raise_for_status()
    result = response.json()
    ttl_cache.set(cache_key, result)
    return result
