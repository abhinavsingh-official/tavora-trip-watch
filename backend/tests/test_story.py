"""app/story.py - extracting real alternative flights/hotels from a raw
supplier response already stored on an observation. Fixtures below mirror
the real Sabre/Hotelbeds response shapes confirmed in app/sources/*.py and
docs/DATA_SOURCE_DOSSIER.md, not invented structures.
"""

from app.story import extract_flight_candidates, extract_hotel_candidates


def _sabre_fixture(itineraries: list[tuple[str, int, float]]) -> dict:
    """Builds a minimal Sabre BFM v4-shaped response for the given
    (carrier_code, flight_number, inr_price) tuples - one leg/schedule per
    itinerary, which is all app/story.py actually reads."""
    leg_descs = []
    schedule_descs = []
    itins = []
    for i, (carrier, flight_number, price) in enumerate(itineraries, start=1):
        schedule_descs.append(
            {
                "id": i,
                "carrier": {"marketing": carrier, "marketingFlightNumber": flight_number},
                "departure": {"airport": "BOM", "time": "10:00:00+05:30"},
                "arrival": {"airport": "GOI", "time": "11:30:00+05:30"},
                "stopCount": 0,
            }
        )
        leg_descs.append({"id": i, "schedules": [{"ref": i}]})
        itins.append(
            {
                "legs": [{"ref": i}],
                "pricingInformation": [
                    {
                        "fare": {
                            "totalFare": {
                                "baseFareCurrency": "INR",
                                "baseFareAmount": price,
                            }
                        }
                    }
                ],
            }
        )
    return {
        "groupedItineraryResponse": {
            "legDescs": leg_descs,
            "scheduleDescs": schedule_descs,
            "itineraryGroups": [{"itineraries": itins}],
        }
    }


def test_extract_flight_candidates_sorted_cheapest_first():
    raw = _sabre_fixture([("IX", 100, 9000.0), ("AI", 200, 7000.0), ("6E", 300, 8000.0)])
    candidates = extract_flight_candidates(raw)
    assert [c["price_inr"] for c in candidates] == [7000.0, 8000.0, 9000.0]
    assert candidates[0]["carrier_code"] == "AI"


def test_extract_flight_candidates_ignores_non_inr_fares():
    raw = _sabre_fixture([("IX", 100, 9000.0)])
    raw["groupedItineraryResponse"]["itineraryGroups"][0]["itineraries"][0]["pricingInformation"][
        0
    ]["fare"]["totalFare"]["baseFareCurrency"] = "USD"
    assert extract_flight_candidates(raw) == []


def test_extract_flight_candidates_handles_missing_raw():
    assert extract_flight_candidates(None) == []
    assert extract_flight_candidates({}) == []


def test_extract_flight_candidates_caps_at_five():
    raw = _sabre_fixture([("IX", i, 7000.0 + i) for i in range(10)])
    assert len(extract_flight_candidates(raw)) == 5


def _hotelbeds_fixture(hotels: list[tuple[str, str, float]]) -> dict:
    return {
        "hotels": {
            "hotels": [
                {
                    "name": name,
                    "categoryName": category,
                    "rooms": [{"rates": [{"net": str(price_eur)}]}],
                }
                for name, category, price_eur in hotels
            ]
        }
    }


def test_extract_hotel_candidates_converts_eur_to_inr_and_sorts():
    raw = _hotelbeds_fixture(
        [("Cheap Inn", "3 STARS", 100.0), ("Fancy Resort", "5 STARS", 50.0)]
    )
    candidates = extract_hotel_candidates(raw, min_star_rating=0)
    assert candidates[0]["name"] == "Fancy Resort"  # 50 EUR is cheaper than 100 EUR
    assert candidates[0]["price_inr"] > 0


def test_extract_hotel_candidates_respects_minimum_star_rating():
    raw = _hotelbeds_fixture([("Budget Place", "2 STARS", 50.0), ("Nice Place", "4 STARS", 80.0)])
    candidates = extract_hotel_candidates(raw, min_star_rating=3)
    assert len(candidates) == 1
    assert candidates[0]["name"] == "Nice Place"


def test_extract_hotel_candidates_handles_missing_raw():
    assert extract_hotel_candidates(None, min_star_rating=0) == []
