"""
Simulated cab/transfer pricing - no real fare-source candidate exists for
this category after six research rounds (docs/internal/research-summary.md Sec. 6.4/7.3:
Ola's and CabBazar's own documented APIs are the strongest real precedents
found, both gated B2B-only). Previously a single fixed-quote formula
chosen by adult-count threshold; now reads scripts/generate_synthetic_data.py's
SyntheticCabOption directory - several labeled vehicle classes (vendor
name, passenger capacity, luggage capacity, per-leg price), anchored to
the same real reference numbers (official per-km RTO rate cards, the real
₹20-28/km tempo-traveller market range) this file already cited. This is
also the first real enforcement of Sec. 05's cab passenger/luggage
capacity requirement - a request whose party/baggage genuinely exceeds
every available vehicle class now reports "unavailable" rather than
silently fitting them into something too small; none of the three real
demo users are large enough to ever trigger that, by design.
"""

from sqlalchemy.orm import Session

from app.models import SyntheticCabOption

"""
A request with checked baggage needs at least one bag's worth of luggage
space per adult - a simple, documented assumption (not a real supplier's
own baggage policy, since none exists for this category), not a precise
airline-style allowance.
"""
MIN_LUGGAGE_CAPACITY_PER_ADULT_IF_CHECKED = 1


def _eligible_options(adults: int, checked_baggage: bool, db: Session) -> list[SyntheticCabOption]:
    query = db.query(SyntheticCabOption).filter(SyntheticCabOption.passenger_capacity >= adults)
    if checked_baggage:
        query = query.filter(
            SyntheticCabOption.luggage_capacity >= adults * MIN_LUGGAGE_CAPACITY_PER_ADULT_IF_CHECKED
        )
    return query.order_by(SyntheticCabOption.current_price_per_leg_inr.asc()).all()


def get_cab_candidates(trip_request, db: Session) -> list[dict]:
    """For the "Your Bookings" directory UI - every real eligible vehicle
    class, cheapest first."""
    return [
        {
            "vendor_name": row.vendor_name,
            "vehicle_class": row.vehicle_class,
            "passenger_capacity": row.passenger_capacity,
            "luggage_capacity": row.luggage_capacity,
            "price_per_leg_inr": row.current_price_per_leg_inr,
        }
        for row in _eligible_options(trip_request.adults, trip_request.checked_baggage, db)
    ]


def get_cab_prices(trip_request, db: Session) -> dict:
    eligible = _eligible_options(trip_request.adults, trip_request.checked_baggage, db)
    if not eligible:
        return {
            "outbound_price": None,
            "return_price": None,
            "status": "unavailable",
            "source": "simulated",
            "raw": None,
        }

    cheapest = eligible[0]
    per_leg = cheapest.current_price_per_leg_inr
    return {
        "outbound_price": per_leg,
        "return_price": per_leg,
        "status": "complete",
        "source": "simulated",
        "raw": {"vendor_name": cheapest.vendor_name, "vehicle_class": cheapest.vehicle_class},
    }
