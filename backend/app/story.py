"""Extracts the real alternative flights/hotels that were already fetched
alongside the one price that actually gets used (app/pricing.py always picks
the single cheapest eligible option - this module surfaces the others, for
the "trip story" view, Sec. 10's own "show what is known" framing taken
further for usability's sake).

Nothing here changes a single number anywhere else in the app: this reads
`PriceObservation.raw_sources` - the full raw Sabre/Hotelbeds response
already stored for every check - and never calls a real supplier itself.
Zero new real API calls; this is a presentation layer over data the system
already paid for and already has.
"""

from app.sources.hotels import EUR_TO_INR_RATE, _star_count

MAX_CANDIDATES = 5


def extract_flight_candidates(raw_leg_response: dict | None) -> list[dict]:
    """raw_leg_response is one leg's raw Sabre Bargain Finder Max v4
    response (app/sources/flights.py calls Sabre once per leg) - a
    reference-based structure where itineraries point at legDescs, which
    point at scheduleDescs, which carry the actual carrier/time/airport
    fields. Returns the cheapest MAX_CANDIDATES real itineraries, same
    INR-only filter app/sources/flights.py itself applies, so "the
    cheapest one here" always matches what the real price breakdown shows.
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
    """Mirrors app/sources/hotels.py's own eligibility filter (star rating)
    and EUR->INR conversion exactly, so "the cheapest eligible one here"
    always matches the real stored hotel_total_price."""
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
