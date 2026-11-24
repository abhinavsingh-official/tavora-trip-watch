"""
Drifts the synthetic flight/cab directories and the cached hotel directory
slightly over time, so repeated monitoring cycles actually show a changing
total. Without this, Sabre's frozen test fares and a one-time hotel/cab
snapshot would never move, and "keep checking, alert on a drop" would have
nothing to demonstrate.

Called from scheduler.py each real cycle, and from POST /api/lab/mutate-prices
for an on-demand nudge during a demo.

Clamped to +/-30% of the original base price so it drifts instead of
wandering off into something absurd over a long demo session.
"""

import random

from sqlalchemy.orm import Session

from app.models import CachedHotelOption, SyntheticCabOption, SyntheticFlightOption
from app.sim_clock import sim_clock

"""
Small step size - prices should drift, not jump - and intentionally
unseeded, unlike generate_synthetic_data.py which needs to be replayable.
This just needs to look alive.
"""
STEP_FRACTION = 0.04
MAX_DRIFT_FROM_BASE = 0.30


def _nudge(current: float, base: float) -> float:
    step = current * random.uniform(-STEP_FRACTION, STEP_FRACTION)
    nudged = current + step
    floor = base * (1 - MAX_DRIFT_FROM_BASE)
    ceiling = base * (1 + MAX_DRIFT_FROM_BASE)
    return round(min(max(nudged, floor), ceiling), 2)


def mutate_all_prices(db: Session) -> dict:
    now = sim_clock.get_now()

    flight_rows = db.query(SyntheticFlightOption).all()
    for row in flight_rows:
        row.current_price_inr = _nudge(row.current_price_inr, row.base_price_inr)
        row.last_mutated_at = now

    cab_rows = db.query(SyntheticCabOption).all()
    for row in cab_rows:
        row.current_price_per_leg_inr = _nudge(row.current_price_per_leg_inr, row.base_price_per_leg_inr)
        row.last_mutated_at = now

    hotel_rows = db.query(CachedHotelOption).all()
    for row in hotel_rows:
        row.price_eur = _nudge(row.price_eur, row.base_price_eur)
        row.fetched_at = now

    db.commit()
    return {
        "flights_mutated": len(flight_rows),
        "cabs_mutated": len(cab_rows),
        "hotels_mutated": len(hotel_rows),
    }
