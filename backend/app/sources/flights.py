"""Real sandbox flight prices via Sabre Bargain Finder Max v4.

Confirmed working against a real BOM<->GOI query, docs/internal/research-notes-raw.md round 9. Sabre's
own response includes an INR-denominated field directly (baseFareAmount /
baseFareCurrency) - no currency conversion needed for flights, unlike hotels.
"""

import logging

from app import sabre_client

logger = logging.getLogger(__name__)

"""City name -> IATA airport code, for the three mock users' routes
(docs/assignment.pdf Sec. 02). Extend here if a later version adds routes.
"""
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


def _search_leg(origin_city: str, destination_city: str, travel_date: str, adults: int) -> dict:
    origin_code = AIRPORT_CODES.get(origin_city.upper())
    destination_code = AIRPORT_CODES.get(destination_city.upper())
    if not origin_code or not destination_code:
        return {"price": None, "status": "unavailable", "raw": None}

    try:
        raw = sabre_client.search_flights(origin_code, destination_code, travel_date, adults)
    except Exception:
        """A real supplier call can fail (network, rate limit, no results) -
        that must show up as "unavailable", never a silent zero (Sec. 05).
        Logged, not swallowed - without this, a real outage looks identical
        to "no flights exist," which defeats Sec. 13's "diagnose an unseen
        supplier failure" live-review requirement.
        """
        logger.exception(
            "Sabre flight search failed for %s -> %s on %s", origin_code, destination_code, travel_date
        )
        return {"price": None, "status": "unavailable", "raw": None}

    price = _cheapest_total_inr(raw)
    if price is None:
        return {"price": None, "status": "unavailable", "raw": raw}

    return {"price": price, "status": "complete", "raw": raw}


def get_flight_prices(trip_request) -> dict:
    outbound = _search_leg(
        trip_request.origin,
        trip_request.destination,
        trip_request.outbound_date.isoformat(),
        trip_request.adults,
    )
    inbound = _search_leg(
        trip_request.destination,
        trip_request.origin,
        trip_request.return_date.isoformat(),
        trip_request.adults,
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
        "source": "real-sandbox:sabre-bfm-v4",
        "raw": {"outbound": outbound["raw"], "return": inbound["raw"]},
    }
