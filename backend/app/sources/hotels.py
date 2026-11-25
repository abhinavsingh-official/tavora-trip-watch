"""Real sandbox hotel prices via Hotelbeds Apitude. EUR rates are converted at a fixed rate rather than
left "provisional", or a hotel package could never reach "complete" and trigger a budget alert."""

import logging
import re

from sqlalchemy.orm import Session

from app import hotelbeds_client
from app.models import CachedHotelOption

logger = logging.getLogger(__name__)

EUR_TO_INR_RATE = 95.0  # fixed approximate rate, not a live FX feed


def _star_count(category_name: str | None) -> int:
    if not category_name:
        return 0
    match = re.search(r"(\d+)", category_name)
    return int(match.group(1)) if match else 0


def _cheapest_eligible_room_eur(raw_response: dict, min_star_rating: int, rooms: int) -> float | None:
    """Duplicate rateKeys in a room type are the same per-room rate repeated, not separate prices - dedupe first."""
    hotels = raw_response.get("hotels", {}).get("hotels", [])
    per_room_prices = []
    for hotel in hotels:
        if _star_count(hotel.get("categoryName")) < min_star_rating:
            continue
        for room in hotel.get("rooms", []):
            seen_rate_keys = set()
            for rate in room.get("rates", []):
                rate_key = rate.get("rateKey")
                if rate_key in seen_rate_keys:
                    continue
                seen_rate_keys.add(rate_key)
                per_room_prices.append(float(rate["net"]))
    return min(per_room_prices) * rooms if per_room_prices else None


def _cached_candidates(trip_request, db: Session) -> list[CachedHotelOption]:
    """Reads pre-fetched Hotelbeds rows for this search key; price_eur is already the full multi-room total."""
    return (
        db.query(CachedHotelOption)
        .filter(
            CachedHotelOption.destination == trip_request.destination.upper(),
            CachedHotelOption.check_in == trip_request.outbound_date,
            CachedHotelOption.check_out == trip_request.return_date,
            CachedHotelOption.rooms == trip_request.rooms,
            CachedHotelOption.adults == trip_request.adults,
            CachedHotelOption.star_rating >= trip_request.min_star_rating,
        )
        .order_by(CachedHotelOption.price_eur.asc())
        .all()
    )


def get_hotel_candidates(trip_request, db: Session) -> list[dict]:
    """Every cached hotel option eligible for this request, cheapest first, for the directory UI."""
    return [
        {
            "hotel_name": row.hotel_name,
            "category_name": row.category_name,
            "star_rating": row.star_rating,
            "room_description": row.room_description,
            "price_eur": row.price_eur,
            "price_inr": round(row.price_eur * EUR_TO_INR_RATE, 2),
        }
        for row in _cached_candidates(trip_request, db)
    ]


def get_hotel_price(trip_request, db: Session) -> dict:
    cached = _cached_candidates(trip_request, db)
    if cached:
        cheapest = cached[0]
        return {
            "price": round(cheapest.price_eur * EUR_TO_INR_RATE, 2),
            "price_eur": cheapest.price_eur,
            "conversion_rate": EUR_TO_INR_RATE,
            "status": "complete",
            "source": "real-sandbox:hotelbeds-cached",
            "currency_note": "approximate - EUR-sourced, converted at a fixed rate, not a live FX feed",
            "raw": {"cached_hotel_name": cheapest.hotel_name, "cached_hotel_code": cheapest.hotel_code},
        }

    # No cached row for this search key; falls back to a real live call
    try:
        raw = hotelbeds_client.search_hotels(
            destination=trip_request.destination,
            check_in=trip_request.outbound_date.isoformat(),
            check_out=trip_request.return_date.isoformat(),
            rooms=trip_request.rooms,
            adults=trip_request.adults,
        )
    except Exception:
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

    price_eur = _cheapest_eligible_room_eur(raw, trip_request.min_star_rating, trip_request.rooms)
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
        "currency_note": "approximate - EUR-sourced, converted at a fixed rate, not a live FX feed",
        "raw": raw,
    }
