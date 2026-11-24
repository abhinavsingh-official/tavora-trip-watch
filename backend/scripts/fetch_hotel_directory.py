"""
One-time bulk fetch of real Hotelbeds hotel inventory for the three demo
users' exact (destination, dates, occupancy) search keys, using the
fallback sandbox account (see app/config.py's
hotelbeds_fallback_hotel_api_key/secret) so the live request path's 50/day
primary-account quota is never touched by this.

Run once (or re-run occasionally to refresh): .venv/bin/python
scripts/fetch_hotel_directory.py

Every real hotel + its cheapest eligible rate line found is stored as one
CachedHotelOption row. hotels.py reads from this table for the live
product; this script is never imported by the running app.
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
The three demo users' exact search keys (origin/other fields don't matter
for a hotel search - only destination/dates/occupancy do), from
scripts/seed.py's Sec. 02 values. Radius widened from the live path's
default 30km to try to surface closer to ~30 real hotels per destination in
one call, since this is a one-time bulk fetch, not a per-check search.
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
    Dedupe by rateKey first - Hotelbeds echoes one identical rate line per
    requested room-occupancy block (confirmed: splitting a 2-room search
    into 2 occupancy entries returns 2 duplicate lines per room type, not
    2 independent prices), then multiply the genuine per-room cheapest
    rate by the real room count. Same logic as app/sources/hotels.py's
    _cheapest_eligible_room_eur, kept here as its own copy since this
    script never imports from the live request path on purpose.
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
            """Idempotent re-run: clear this exact search key's old rows
            first, so re-running after a payload/pricing fix replaces
            stale data instead of duplicating it.
            """
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
