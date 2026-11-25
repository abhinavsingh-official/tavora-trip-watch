"""
Real bug, reported live: displayed prices seemed to only ever drop, never
rise, across a long session. Root cause - every row nudged independently,
then the app always shows the *cheapest* row in the group. Repeatedly
sampling the minimum of several independent random walks drifts down even
though each individual walk is symmetric (whichever row got unlucky keeps
winning "cheapest"). Fixed by nudging every row in the same market
(same route/date for flights, same search key for hotels, the whole cab
list at once) by one shared step, so the group's cheapest price still
moves both ways with the market.
"""

from datetime import date

import pytest

from app.models import SyntheticFlightOption, TripRequest
from app.price_mutation import apply_manual_shock, mutate_all_prices


@pytest.fixture(autouse=True)
def _never_stagnant(monkeypatch):
    """Most tests in this file want a guaranteed move to assert against - force every group to
    mutate. test_a_stagnant_group_is_left_unchanged below overrides this to test the opposite."""
    monkeypatch.setattr("app.price_mutation._group_is_stagnant_this_cycle", lambda: False)


def _make_flight(db, *, origin="BOM", destination="GOI", travel_date=date(2026, 12, 26), price=5000.0):
    row = SyntheticFlightOption(
        origin_code=origin,
        destination_code=destination,
        travel_date=travel_date,
        carrier_code="6E",
        carrier_name="IndiGo",
        flight_number=101,
        departure_time="10:00",
        arrival_time="12:00",
        stops=0,
        base_price_inr=price,
        current_price_inr=price,
    )
    db.add(row)
    return row


def test_every_option_on_the_same_route_moves_by_the_same_step(db):
    a = _make_flight(db, price=5000.0)
    b = _make_flight(db, price=5000.0)
    c = _make_flight(db, price=5000.0)
    db.commit()

    mutate_all_prices(db)
    db.refresh(a)
    db.refresh(b)
    db.refresh(c)

    # Same starting price, same route+date -> same shared step, so still equal.
    assert a.current_price_inr == b.current_price_inr == c.current_price_inr
    # And it's not a no-op - the shared step is almost never exactly zero.
    assert a.current_price_inr != 5000.0


def test_different_routes_move_independently(db):
    bom_goi = _make_flight(db, origin="BOM", destination="GOI", price=5000.0)
    del_goi = _make_flight(db, origin="DEL", destination="GOI", price=5000.0)
    db.commit()

    mutate_all_prices(db)
    db.refresh(bom_goi)
    db.refresh(del_goi)

    # Different routes are different markets - no reason their steps should match.
    # (Flaky only in the astronomically unlikely case two independent random
    # draws land on the exact same float - acceptable for a demo-data test.)
    assert bom_goi.current_price_inr != del_goi.current_price_inr


def test_manual_shock_moves_only_this_trips_own_market(db, two_users):
    """The Simulation page's shock slider - an exact, signed, guaranteed
    move, scoped to just the one trip's own route+dates, never the whole
    directory."""
    user_a, _ = two_users
    trip_request = TripRequest(
        user_id=user_a.id,
        origin="Mumbai",
        destination="Goa",
        outbound_date=date(2026, 12, 26),
        return_date=date(2026, 12, 29),
        adults=2,
        rooms=1,
        budget_inr=35000,
    )
    db.add(trip_request)
    db.commit()
    db.refresh(trip_request)

    this_trips_flight = _make_flight(db, origin="BOM", destination="GOI", travel_date=date(2026, 12, 26), price=5000.0)
    other_route_flight = _make_flight(db, origin="DEL", destination="GOI", travel_date=date(2026, 12, 26), price=5000.0)
    db.commit()

    apply_manual_shock(db, trip_request, 0.2)
    db.refresh(this_trips_flight)
    db.refresh(other_route_flight)

    assert this_trips_flight.current_price_inr == 6000.0
    assert other_route_flight.current_price_inr == 5000.0


def test_a_stagnant_group_is_left_unchanged(db, monkeypatch):
    """Known-issue fix: background drift used to be gated behind an in-memory cycle counter that
    reset to 0 on every process restart, so it could go a very long time without ever actually
    moving a price - that's what looked "frozen". Replaced with a per-group, per-cycle coin flip
    that doesn't depend on process uptime at all; this test is the "stayed still" half of it."""
    monkeypatch.setattr("app.price_mutation._group_is_stagnant_this_cycle", lambda: True)
    row = _make_flight(db, price=5000.0)
    db.commit()

    result = mutate_all_prices(db)
    db.refresh(row)

    assert row.current_price_inr == 5000.0
    assert result["flights_mutated"] == 0


def test_mutated_counts_reflect_only_the_groups_that_actually_moved(db):
    a = _make_flight(db, origin="BOM", destination="GOI", price=5000.0)
    b = _make_flight(db, origin="DEL", destination="GOI", price=5000.0)
    db.commit()

    result = mutate_all_prices(db)
    db.refresh(a)
    db.refresh(b)

    assert result["flights_mutated"] == 2
    assert a.current_price_inr != 5000.0
    assert b.current_price_inr != 5000.0


def test_nudge_reflects_off_the_drift_boundary_instead_of_flatlining():
    from app.price_mutation import _nudge

    base = 10000.0
    floor = base * 0.70
    # A step big enough to overshoot the floor by 500
    nudged = _nudge(floor + 100, base, step_fraction=-0.06)
    # Reflected back inside the band, not clamped flat at the floor
    assert nudged != floor
    assert floor <= nudged <= base * 1.30
