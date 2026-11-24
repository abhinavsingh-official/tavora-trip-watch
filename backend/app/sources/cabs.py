"""
Simulated cab/transfer pricing - no usable real fare API exists for this
category (Ola and CabBazar are both B2B-only). Reads the SyntheticCabOption
directory instead: a handful of vehicle classes with vendor, passenger
capacity, luggage capacity, and per-leg price, anchored to real per-km rate
cards. A party/baggage combo that exceeds every available vehicle class
reports "unavailable" rather than silently squeezing in.
"""

from sqlalchemy.orm import Session

from app.models import SyntheticCabOption

"""Rough assumption: checked baggage needs at least one bag's worth of
luggage space per adult. Not a real supplier policy, just a stand-in.
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
    """For the directory UI - every eligible vehicle class, cheapest first."""
    return [
        {
            "vendor_name": row.vendor_name,
            "vehicle_class": row.vehicle_class,
            "passenger_capacity": row.passenger_capacity,
            "luggage_capacity": row.luggage_capacity,
            "distance_km": row.distance_km,
            "per_km_rate_inr": row.per_km_rate_inr,
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
