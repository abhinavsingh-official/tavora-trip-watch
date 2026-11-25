"""Flight prices for the live product. Reads the mutated SyntheticFlightOption directory first (Sabre's
sandbox fares never change on their own); anything uncovered falls back to a real Sabre call."""

import logging

from sqlalchemy.orm import Session

from app import sabre_client, schedule_rules
from app.models import SyntheticFlightOption

logger = logging.getLogger(__name__)

# City name -> IATA airport code for the mock users' routes; extend here for more routes
AIRPORT_CODES = {
    "MUMBAI": "BOM",
    "GOA": "GOI",
    "DELHI": "DEL",
    "JAIPUR": "JAI",
}


def _cheapest_total_inr(raw_response: dict) -> float | None:
    """Pulls the cheapest itinerary's INR total out of a BFM v4 response."""
    try:
        groups = raw_response["groupedItineraryResponse"]["itineraryGroups"]
    except KeyError:
        return None

    totals = []
    for group in groups:
        for itinerary in group.get("itineraries", []):
            for pricing in itinerary.get("pricingInformation", []):
                fare = pricing.get("fare", {})
                total_fare = fare.get("totalFare", {})
                if total_fare.get("baseFareCurrency") == "INR":
                    totals.append(float(total_fare["baseFareAmount"]))

    return min(totals) if totals else None


def _cached_leg_candidates(origin_code, destination_code, travel_date, max_stops, is_outbound: bool, db: Session):
    rows = (
        db.query(SyntheticFlightOption)
        .filter(
            SyntheticFlightOption.origin_code == origin_code,
            SyntheticFlightOption.destination_code == destination_code,
            SyntheticFlightOption.travel_date == travel_date,
            SyntheticFlightOption.stops <= max_stops,
        )
        .order_by(SyntheticFlightOption.current_price_inr.asc())
        .all()
    )
    # Drops candidates that violate the transfer-buffer rule entirely (see schedule_rules.py), not just by price
    return [
        row
        for row in rows
        if schedule_rules.satisfies_transfer_buffer(row.departure_time, row.arrival_time, is_outbound)
    ]


def _leg_candidates_as_dicts(origin_code, destination_code, travel_date, max_stops, is_outbound, adults, db: Session) -> list[dict]:
    """For the booking directory UI: every eligible synthetic candidate for
    this leg, priced for the actual adult count."""
    return [
        {
            "carrier_code": row.carrier_code,
            "carrier_name": row.carrier_name,
            "flight_number": row.flight_number,
            "departure_time": row.departure_time,
            "arrival_time": row.arrival_time,
            "stops": row.stops,
            "price_inr": round(row.current_price_inr * adults, 2),
        }
        for row in _cached_leg_candidates(origin_code, destination_code, travel_date, max_stops, is_outbound, db)
    ]


def _search_leg(
    origin_city: str,
    destination_city: str,
    travel_date,
    adults: int,
    max_stops: int,
    is_outbound: bool,
    db: Session,
) -> dict:
    origin_code = AIRPORT_CODES.get(origin_city.upper())
    destination_code = AIRPORT_CODES.get(destination_city.upper())
    if not origin_code or not destination_code:
        return {"price": None, "status": "unavailable", "raw": None}

    cached = _cached_leg_candidates(origin_code, destination_code, travel_date, max_stops, is_outbound, db)
    if cached:
        cheapest = cached[0]
        total = round(cheapest.current_price_inr * adults, 2)
        return {
            "price": total,
            "status": "complete",
            "raw": {
                "synthetic_carrier": cheapest.carrier_name,
                "synthetic_flight_number": cheapest.flight_number,
            },
        }

    # No synthetic row for this combo; falls back to real Sabre, which isn't filtered by max-stops
    try:
        raw = sabre_client.search_flights(origin_code, destination_code, travel_date.isoformat(), adults)
    except Exception:
        # logged so a real outage is distinguishable from "no flights exist"
        logger.exception(
            "Sabre flight search failed for %s -> %s on %s", origin_code, destination_code, travel_date
        )
        return {"price": None, "status": "unavailable", "raw": None}

    price = _cheapest_total_inr(raw)
    if price is None:
        return {"price": None, "status": "unavailable", "raw": raw}

    return {"price": price, "status": "complete", "raw": raw}


def get_flight_candidates(trip_request, db: Session) -> dict:
    return {
        "outbound": _leg_candidates_as_dicts(
            AIRPORT_CODES.get(trip_request.origin.upper()),
            AIRPORT_CODES.get(trip_request.destination.upper()),
            trip_request.outbound_date,
            trip_request.max_stops_outbound,
            True,
            trip_request.adults,
            db,
        ),
        "return": _leg_candidates_as_dicts(
            AIRPORT_CODES.get(trip_request.destination.upper()),
            AIRPORT_CODES.get(trip_request.origin.upper()),
            trip_request.return_date,
            trip_request.max_stops_return,
            False,
            trip_request.adults,
            db,
        ),
    }


def get_flight_prices(trip_request, db: Session) -> dict:
    outbound = _search_leg(
        trip_request.origin,
        trip_request.destination,
        trip_request.outbound_date,
        trip_request.adults,
        trip_request.max_stops_outbound,
        True,
        db,
    )
    inbound = _search_leg(
        trip_request.destination,
        trip_request.origin,
        trip_request.return_date,
        trip_request.adults,
        trip_request.max_stops_return,
        False,
        db,
    )

    status = (
        "complete"
        if outbound["status"] == "complete" and inbound["status"] == "complete"
        else "unavailable"
    )

    return {
        "outbound_price": outbound["price"],
        "return_price": inbound["price"],
        "status": status,
        "source": "synthetic" if "synthetic_carrier" in (outbound["raw"] or {}) else "real-sandbox:sabre-bfm-v4",
        "raw": {"outbound": outbound["raw"], "return": inbound["raw"]},
    }
