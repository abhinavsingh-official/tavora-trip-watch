"""Thin client for Hotelbeds Apitude (confirmed working, docs/internal/research-notes-raw.md rounds 10-13).

Auth: a per-request signature, SHA256(apikey + secret + unix_timestamp) - this
can't be cached like Sabre's token, since it's timestamp-based and must be
freshly computed for every call.

Destination codes are not guessable from city names or IATA codes (round 11
found this the hard way - "GOA" is Genoa, Italy; "GOI" is Goiania, Brazil in
Hotelbeds' own system). Searching by geolocation instead is what actually
works, so known destinations' coordinates are hardcoded here rather than
resolved via a content-API lookup at runtime - that also protects the free
key's 50/day quota, which is consumed by content calls, not search calls.
"""

import hashlib
import time

import httpx

from app import rate_limit, ttl_cache
from app.config import get_settings

settings = get_settings()

"""Keeps us under Hotelbeds' documented "8 requests per 4 seconds" burst limit
(from the credentials page, not guessed) - without this, a burst of checks
could get throttled by Hotelbeds itself, and that throttling would currently
be indistinguishable from "no hotels found" once it hits the generic
exception handler in sources/hotels.py.
"""
_MIN_CALL_INTERVAL_SECONDS = 0.6

"""Absorbs rapid repeats (double-clicks, a page re-fetching on mount) without
changing how often a *meaningfully new* real check happens - see ttl_cache.py.
"""
_CACHE_TTL_SECONDS = 240

"""(latitude, longitude) - confirmed reachable via a real geolocation search,
round 11 (Goa) and resolvable the same way for any other destination needed.
"""
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
    api_key/secret default to the primary live-request-path credentials.
    backend/scripts/fetch_hotel_directory.py passes the fallback account's
    credentials explicitly instead - the one-time bulk seed fetch, never the
    live path. radius_km defaults to 30 (the original, confirmed-working
    value); the seed script widens it to pull closer to ~30 real hotels per
    destination in one call.
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
    Undocumented, discovered directly (not in Hotelbeds' own docs): the
    occupancies array is one entry PER ROOM, each describing that one
    room's own adults - not a single entry with "rooms" as a multiplier.
    Sending {"rooms": 2, "adults": 4} as one combined entry is a malformed
    request that most hotels can't actually answer (confirmed: it returned
    5 priced hotels for Goa; the equivalent correctly-split request
    returned 47 for the exact same search). Adults are split as evenly as
    possible across the requested room count.
    """
    base_adults_per_room, remainder = divmod(adults, rooms)
    occupancies = [
        {
            "rooms": 1,
            "adults": base_adults_per_room + (1 if i < remainder else 0),
            "children": 0,
        }
        for i in range(rooms)
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
