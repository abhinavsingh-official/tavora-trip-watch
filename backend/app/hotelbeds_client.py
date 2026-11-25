"""Thin client for Hotelbeds Apitude. Searches by geolocation since Hotelbeds' own
destination codes are misleading (e.g. "GOA" is Genoa, not Goa)."""

import hashlib
import time

import httpx

from app import rate_limit, ttl_cache
from app.config import get_settings

settings = get_settings()

_MIN_CALL_INTERVAL_SECONDS = 0.6  # stay under Hotelbeds' burst limit (8 req/4s); throttling looks like "no hotels found"
_CACHE_TTL_SECONDS = 240  # absorbs rapid repeats without changing how often we hit Hotelbeds for a fresh price

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
    # api_key/secret default to the primary account; fetch_hotel_directory.py passes the fallback account's
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

    # Hotelbeds needs one occupancies entry per room (not "rooms" as a multiplier), and rejects a room with 0 adults
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
