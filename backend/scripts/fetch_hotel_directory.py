"""
One-time bulk fetch of real Hotelbeds inventory for the three demo users'
(destination, dates, occupancy) search keys. Uses the fallback sandbox
account so this doesn't eat into the primary account's 50/day quota.

Run once (or re-run to refresh): .venv/bin/python scripts/fetch_hotel_directory.py

Each hotel's cheapest eligible rate gets stored as a CachedHotelOption row.
hotels.py reads from that table; this script is never imported by the app.
"""

import sys
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app import hotelbeds_client
from app.config import get_settings
from app.database import SessionLocal
from app.models import CachedHotelOption

settings = get_settings()

"""
Search keys for the three demo users (only destination/dates/occupancy
matter for a hotel search). Radius is widened past the live path's default
30km to pull in more hotels per destination since this is a one-time bulk
fetch, not a per-check search.
"""
SEARCH_KEYS = [
    {"label": "User A (Goa)", "destination": "GOA", "check_in": date(2026, 12, 26), "check_out": date(2026, 12, 29), "rooms": 1, "adults": 2},
    {"label": "User B (Goa)", "destination": "GOA", "check_in": date(2026, 12, 26), "check_out": date(2026, 12, 29), "rooms": 2, "adults": 4},
    {"label": "User C (Jaipur)", "destination": "JAIPUR", "check_in": date(2026, 12, 26), "check_out": date(2026, 12, 28), "rooms": 1, "adults": 2},
]
SEARCH_RADIUS_KM = 60


def _star_count(category_name: str | None) -> int:
    import re

    if not category_name:
        return 0
    match = re.search(r"(\d+)", category_name)
    return int(match.group(1)) if match else 0


def _cheapest_rate_eur(hotel: dict, rooms: int) -> float | None:
    """
    Hotelbeds echoes one duplicate rate line per room-occupancy block, so
    dedupe by rateKey first, then multiply the real per-room cheapest rate
    by room count. Mirrors app/sources/hotels.py's
    _cheapest_eligible_room_eur, duplicated here since this script shouldn't
    import from the live request path.
    """
    per_room_prices = []
    for room in hotel.get("rooms", []):
        seen_rate_keys = set()
        for rate in room.get("rates", []):
            rate_key = rate.get("rateKey")
            if rate_key in seen_rate_keys:
                continue
            seen_rate_keys.add(rate_key)
            per_room_prices.append(float(rate["net"]))
    return min(per_room_prices) * rooms if per_room_prices else None


def _room_description(hotel: dict) -> str | None:
    rooms = hotel.get("rooms", [])
    return rooms[0].get("name") if rooms and rooms[0].get("name") else None


def fetch_and_store():
    if not settings.hotelbeds_fallback_hotel_api_key:
        print("No fallback credentials configured (HOTELBEDS_FALLBACK_HOTEL_API_KEY) - aborting.")
        return

    db = SessionLocal()
    try:
        total_stored = 0
        for key in SEARCH_KEYS:
            # Clear old rows for this search key first, so re-running
            # replaces stale data instead of duplicating it.
            db.query(CachedHotelOption).filter(
                CachedHotelOption.destination == key["destination"],
                CachedHotelOption.check_in == key["check_in"],
                CachedHotelOption.check_out == key["check_out"],
                CachedHotelOption.rooms == key["rooms"],
                CachedHotelOption.adults == key["adults"],
            ).delete()

            print(f"Fetching real hotels for {key['label']}...")
            raw = hotelbeds_client.search_hotels(
                destination=key["destination"],
                check_in=key["check_in"].isoformat(),
                check_out=key["check_out"].isoformat(),
                rooms=key["rooms"],
                adults=key["adults"],
                api_key=settings.hotelbeds_fallback_hotel_api_key,
                secret=settings.hotelbeds_fallback_hotel_secret,
                radius_km=SEARCH_RADIUS_KM,
            )

            hotels = raw.get("hotels", {}).get("hotels", [])
            print(f"  -> {len(hotels)} real hotels returned.")

            stored_for_key = 0
            for hotel in hotels:
                price_eur = _cheapest_rate_eur(hotel, key["rooms"])
                if price_eur is None:
                    continue
                db.add(
                    CachedHotelOption(
                        destination=key["destination"],
                        check_in=key["check_in"],
                        check_out=key["check_out"],
                        rooms=key["rooms"],
                        adults=key["adults"],
                        hotel_code=hotel.get("code"),
                        hotel_name=hotel.get("name", "Unnamed hotel"),
                        category_name=hotel.get("categoryName"),
                        star_rating=_star_count(hotel.get("categoryName")),
                        room_description=_room_description(hotel),
                        base_price_eur=price_eur,
                        price_eur=price_eur,
                    )
                )
                stored_for_key += 1
            db.commit()
            total_stored += stored_for_key
            print(f"  -> {stored_for_key} stored with a usable rate.")

        print(f"Done. {total_stored} real hotel options cached in total.")
    finally:
        db.close()


if __name__ == "__main__":
    fetch_and_store()
