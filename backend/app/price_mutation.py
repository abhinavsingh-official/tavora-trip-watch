"""Drifts synthetic/cached prices over time, per market group (not per row) to avoid biasing the cheapest option downward."""

import random
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models import CachedHotelOption, SyntheticCabOption, SyntheticFlightOption, TripRequest
from app.sim_clock import sim_clock
from app.sources.flights import AIRPORT_CODES

# Small step (drift, not jump); intentionally unseeded unlike generate_synthetic_data.py
STEP_FRACTION = 0.04
MAX_DRIFT_FROM_BASE = 0.30


def _nudge(current: float, base: float, step_fraction: float) -> float:
    # Step sized off `base`, not `current`, so a price that dipped low isn't stuck taking smaller steps back out
    step = base * step_fraction
    nudged = current + step
    floor = base * (1 - MAX_DRIFT_FROM_BASE)
    ceiling = base * (1 + MAX_DRIFT_FROM_BASE)
    return round(min(max(nudged, floor), ceiling), 2)


# Holds prices steady for a few cycles so it doesn't look too jumpy; the "Nudge now" lab control bypasses this
CYCLES_BETWEEN_SCHEDULED_MUTATIONS = 4
_scheduled_cycle_count = 0


def maybe_mutate_all_prices(db: Session) -> dict | None:
    global _scheduled_cycle_count
    _scheduled_cycle_count += 1
    if _scheduled_cycle_count % CYCLES_BETWEEN_SCHEDULED_MUTATIONS != 0:
        return None
    return mutate_all_prices(db)


def mutate_all_prices(db: Session) -> dict:
    now = sim_clock.get_now()

    # One route = one market. Every option on that route moves together.
    flight_rows = db.query(SyntheticFlightOption).all()
    flight_groups: dict[tuple, list[SyntheticFlightOption]] = defaultdict(list)
    for row in flight_rows:
        flight_groups[(row.origin_code, row.destination_code, row.travel_date)].append(row)
    for group in flight_groups.values():
        step_fraction = random.uniform(-STEP_FRACTION, STEP_FRACTION)
        for row in group:
            row.current_price_inr = _nudge(row.current_price_inr, row.base_price_inr, step_fraction)
            row.last_mutated_at = now

    # Cabs are route-agnostic (price depends on vehicle class, not city) - one shared market.
    cab_rows = db.query(SyntheticCabOption).all()
    if cab_rows:
        step_fraction = random.uniform(-STEP_FRACTION, STEP_FRACTION)
        for row in cab_rows:
            row.current_price_per_leg_inr = _nudge(
                row.current_price_per_leg_inr, row.base_price_per_leg_inr, step_fraction
            )
            row.last_mutated_at = now

    # One (destination, dates, occupancy) search key = one market of competing hotels.
    hotel_rows = db.query(CachedHotelOption).all()
    hotel_groups: dict[tuple, list[CachedHotelOption]] = defaultdict(list)
    for row in hotel_rows:
        hotel_groups[(row.destination, row.check_in, row.check_out, row.rooms, row.adults)].append(row)
    for group in hotel_groups.values():
        step_fraction = random.uniform(-STEP_FRACTION, STEP_FRACTION)
        for row in group:
            row.price_eur = _nudge(row.price_eur, row.base_price_eur, step_fraction)
            row.fetched_at = now

    db.commit()
    return {
        "flights_mutated": len(flight_rows),
        "cabs_mutated": len(cab_rows),
        "hotels_mutated": len(hotel_rows),
    }


# Deliberately a separate code path from background drift: an exact, signed move scoped to one trip's market
MANUAL_SHOCK_MAX_FRACTION = 0.60


def _shock_to(base: float, shock_fraction: float) -> float:
    shock_fraction = max(-MANUAL_SHOCK_MAX_FRACTION, min(MANUAL_SHOCK_MAX_FRACTION, shock_fraction))
    return round(base * (1 + shock_fraction), 2)


def apply_manual_shock(db: Session, trip_request: TripRequest, shock_fraction: float) -> dict:
    now = sim_clock.get_now()
    moved = {"flights_mutated": 0, "hotels_mutated": 0, "cabs_mutated": 0}

    origin_code = AIRPORT_CODES.get(trip_request.origin.upper())
    destination_code = AIRPORT_CODES.get(trip_request.destination.upper())
    if origin_code and destination_code:
        for o, d, travel_date in (
            (origin_code, destination_code, trip_request.outbound_date),
            (destination_code, origin_code, trip_request.return_date),
        ):
            rows = (
                db.query(SyntheticFlightOption)
                .filter(
                    SyntheticFlightOption.origin_code == o,
                    SyntheticFlightOption.destination_code == d,
                    SyntheticFlightOption.travel_date == travel_date,
                )
                .all()
            )
            for row in rows:
                row.current_price_inr = _shock_to(row.base_price_inr, shock_fraction)
                row.last_mutated_at = now
            moved["flights_mutated"] += len(rows)

    hotel_rows = (
        db.query(CachedHotelOption)
        .filter(
            CachedHotelOption.destination == trip_request.destination.upper(),
            CachedHotelOption.check_in == trip_request.outbound_date,
            CachedHotelOption.check_out == trip_request.return_date,
            CachedHotelOption.rooms == trip_request.rooms,
            CachedHotelOption.adults == trip_request.adults,
        )
        .all()
    )
    for row in hotel_rows:
        row.price_eur = _shock_to(row.base_price_eur, shock_fraction)
        row.fetched_at = now
    moved["hotels_mutated"] = len(hotel_rows)

    cab_rows = db.query(SyntheticCabOption).all()
    for row in cab_rows:
        row.current_price_per_leg_inr = _shock_to(row.base_price_per_leg_inr, shock_fraction)
        row.last_mutated_at = now
    moved["cabs_mutated"] = len(cab_rows)

    db.commit()
    return moved
