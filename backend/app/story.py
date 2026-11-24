"""Surfaces the flight/hotel alternatives that were already fetched but not
picked - pricing.py always takes the single cheapest eligible option, this
module shows the rest for the "trip story" view.

Pure read of PriceObservation.raw_sources (the raw Sabre/Hotelbeds response
we already stored). No new supplier calls, no effect on any stored price.
"""

from app.sources.hotels import EUR_TO_INR_RATE, _star_count

MAX_CANDIDATES = 5


def extract_flight_candidates(raw_leg_response: dict | None) -> list[dict]:
    """raw_leg_response is one leg's raw Sabre BFM v4 response. It's a
    reference-based structure: itineraries point at legDescs, which point
    at scheduleDescs, which hold the actual carrier/time/airport fields.
    Returns the cheapest MAX_CANDIDATES itineraries, using the same
    INR-only filter sources/flights.py applies, so this matches the real
    price breakdown.
    """
    if not raw_leg_response:
        return []

    gir = raw_leg_response.get("groupedItineraryResponse", {})
    leg_by_id = {leg["id"]: leg for leg in gir.get("legDescs", [])}
    schedule_by_id = {sched["id"]: sched for sched in gir.get("scheduleDescs", [])}

    candidates: list[dict] = []
    for group in gir.get("itineraryGroups", []):
        for itinerary in group.get("itineraries", []):
            legs = itinerary.get("legs", [])
            if not legs:
                continue
            leg = leg_by_id.get(legs[0].get("ref"), {})
            schedules = leg.get("schedules", [])
            if not schedules:
                continue
            schedule = schedule_by_id.get(schedules[0].get("ref"), {})
            carrier = schedule.get("carrier", {})

            for pricing in itinerary.get("pricingInformation", []):
                fare = pricing.get("fare", {}).get("totalFare", {})
                if fare.get("baseFareCurrency") != "INR":
                    continue
                candidates.append(
                    {
                        "carrier_code": carrier.get("marketing"),
                        "flight_number": carrier.get("marketingFlightNumber"),
                        "departure_airport": schedule.get("departure", {}).get("airport"),
                        "arrival_airport": schedule.get("arrival", {}).get("airport"),
                        "departure_time": schedule.get("departure", {}).get("time"),
                        "arrival_time": schedule.get("arrival", {}).get("time"),
                        "stops": schedule.get("stopCount", 0),
                        "price_inr": float(fare["baseFareAmount"]),
                    }
                )

    candidates.sort(key=lambda c: c["price_inr"])
    seen = set()
    unique: list[dict] = []
    for c in candidates:
        key = (c["carrier_code"], c["flight_number"], c["price_inr"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(c)
    return unique[:MAX_CANDIDATES]


def extract_hotel_candidates(raw_response: dict | None, min_star_rating: int) -> list[dict]:
    """Mirrors sources/hotels.py's star-rating filter and EUR->INR
    conversion exactly, so this matches the real stored hotel_total_price.
    """
    if not raw_response:
        return []

    hotels = raw_response.get("hotels", {}).get("hotels", [])
    candidates: list[dict] = []
    for hotel in hotels:
        stars = _star_count(hotel.get("categoryName"))
        if stars < min_star_rating:
            continue
        prices_eur = [
            float(rate["net"])
            for room in hotel.get("rooms", [])
            for rate in room.get("rates", [])
        ]
        if not prices_eur:
            continue
        cheapest_eur = min(prices_eur)
        candidates.append(
            {
                "name": hotel.get("name"),
                "category_name": hotel.get("categoryName"),
                "stars": stars,
                "price_inr": round(cheapest_eur * EUR_TO_INR_RATE, 2),
            }
        )

    candidates.sort(key=lambda c: c["price_inr"])
    return candidates[:MAX_CANDIDATES]
