"""Real sandbox hotel prices via Hotelbeds Apitude.

Confirmed working for Goa via a real geolocation search, docs/NOTES.md round 11.
Currency confirmed EUR via a real CheckRates call, round 13 - not INR, and not
"unconfirmed." Converted here with one documented, labeled fixed rate rather
than treated as provisional, specifically so a hotel-containing package can
still reach "complete" and trigger a budget alert (see docs/DECISIONS.md,
"Pre-code gap check" entry, for why "provisional" would have silently broken
V1's own happy-path demo).
"""

import logging
import re

from app import hotelbeds_client

logger = logging.getLogger(__name__)

# Documented, fixed approximate rate - NOT a live FX feed. Confirmed EUR via a
# real CheckRates call (round 13); this constant is the one place that number
# is applied, so it's easy to find and revise if a better source turns up.
EUR_TO_INR_RATE = 95.0


def _star_count(category_name: str | None) -> int:
    if not category_name:
        return 0
    match = re.search(r"(\d+)", category_name)
    return int(match.group(1)) if match else 0


def _cheapest_eligible_room_eur(raw_response: dict, min_star_rating: int) -> float | None:
    hotels = raw_response.get("hotels", {}).get("hotels", [])
    prices = []
    for hotel in hotels:
        if _star_count(hotel.get("categoryName")) < min_star_rating:
            continue
        for room in hotel.get("rooms", []):
            for rate in room.get("rates", []):
                prices.append(float(rate["net"]))
    return min(prices) if prices else None


def get_hotel_price(trip_request) -> dict:
    try:
        raw = hotelbeds_client.search_hotels(
            destination=trip_request.destination,
            check_in=trip_request.outbound_date.isoformat(),
            check_out=trip_request.return_date.isoformat(),
            rooms=trip_request.rooms,
            adults=trip_request.adults,
        )
    except Exception:
        # Logged, not swallowed - same reasoning as sources/flights.py.
        logger.exception(
            "Hotelbeds search failed for %s (%s -> %s)",
            trip_request.destination,
            trip_request.outbound_date,
            trip_request.return_date,
        )
        return {
            "price": None,
            "status": "unavailable",
            "source": "real-sandbox:hotelbeds",
            "raw": None,
        }

    price_eur = _cheapest_eligible_room_eur(raw, trip_request.min_star_rating)
    if price_eur is None:
        return {
            "price": None,
            "status": "unavailable",
            "source": "real-sandbox:hotelbeds",
            "raw": raw,
        }

    price_inr = round(price_eur * EUR_TO_INR_RATE, 2)

    return {
        "price": price_inr,
        "price_eur": price_eur,
        "conversion_rate": EUR_TO_INR_RATE,
        "status": "complete",
        "source": "real-sandbox:hotelbeds",
        "currency_note": "approximate - EUR-sourced (confirmed via CheckRates, "
        "round 13), converted at a fixed documented rate, not a live FX feed",
        "raw": raw,
    }
