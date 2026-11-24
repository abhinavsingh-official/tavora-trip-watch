"""
Makes the synthetic directories (SyntheticFlightOption, SyntheticCabOption)
and the cached real hotel directory (CachedHotelOption) drift slightly over
time, so repeated real monitoring cycles actually show a changing total -
without this, Sabre's frozen test-cell fares and a one-time hotel/cab
snapshot would never move on their own, and the whole point of "keep
checking and alert on a drop" would have nothing real to demonstrate with
default usage (see docs/internal/decision-log.md's "why monitoring needed a price
mutation layer" entry).

Called two ways:
  - scheduler.py's run_one_cycle(), once per real 5-minute cycle, so
    ordinary usage drifts on its own.
  - POST /api/lab/mutate-prices, for an on-demand nudge during a live
    demo session, since real elapsed time may not cooperate with a review
    window (see routers/lab.py).

Bounded, not a random walk that runs away: every price is clamped to
within +/-30% of its own original base value, so a long-running demo
session still stays in a believable band around the real-anchored
baseline instead of drifting to something absurd.
"""

import random

from sqlalchemy.orm import Session

from app.models import CachedHotelOption, SyntheticCabOption, SyntheticFlightOption
from app.sim_clock import sim_clock

"""
Per-mutation-call step size - deliberately small (prices should drift, not
jump), and deliberately NOT seeded by anything fixed, since the whole
point is to look like real, slightly-unpredictable movement across
repeated cycles - unlike scripts/generate_synthetic_data.py's directory
generation, which IS seeded (that one needs to be exactly replayable;
this one only needs to look alive).
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
