"""Simulated cab/transfer pricing - no real fare-source candidate exists for
this category after six research rounds (docs/research_summary.md Sec. 6.4/7.3:
Ola's and CabBazar's own documented APIs are the strongest real precedents
found, both gated B2B-only). Modeled as a fixed-quote outstation/airport
transfer (Kiwitaxi/Savaari-shaped, not a surge multiplier - round 4), with
vehicle class selected by adult count (round 5), anchored to real reference
numbers: official per-km RTO rate cards and the real ₹20-28/km tempo-traveller
market range, not an arbitrary guess.
"""

ASSUMED_LEG_DISTANCE_KM = 30

SEDAN_FLAT_FARE = 900.0  # ≤3 adults - fixed-quote sedan transfer
TEMPO_RATE_PER_KM = 24.0  # 4+ adults - mid of the real ₹20-28/km market range


def _leg_price(adults: int) -> float:
    if adults <= 3:
        return SEDAN_FLAT_FARE
    return round(ASSUMED_LEG_DISTANCE_KM * TEMPO_RATE_PER_KM, 2)


def get_cab_prices(trip_request) -> dict:
    per_leg = _leg_price(trip_request.adults)
    return {
        "outbound_price": per_leg,
        "return_price": per_leg,
        "status": "complete",
        "source": "simulated",
        "raw": None,
    }
