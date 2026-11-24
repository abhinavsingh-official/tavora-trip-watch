"""
Covers the two newest Simulation levers, added after a real reported bug
(a Dashboard card showing one total while the actual purchase booked a
different one) made clear that "buy now" / "shock the market" needed
their own direct tests, not just manual poking:

- buy_now (app/routers/booking.py): books the current price immediately,
  with no notification to click through first. Shared by the real
  /requests/{id}/buy-now endpoint and /api/lab/book-now.
- apply_manual_shock + /api/lab/shock-and-check: a guaranteed, exact,
  signed price move scoped to one trip's own market, applied and checked
  in a single call.
"""

from datetime import date
from unittest.mock import patch

from app.models import PriceObservation, SyntheticFlightOption


def _create_request(client, user_id, **overrides):
    payload = {
        "user_id": user_id,
        "origin": "Mumbai",
        "destination": "Goa",
        "outbound_date": "2026-12-26",
        "return_date": "2026-12-29",
        "adults": 2,
        "rooms": 1,
        "budget_inr": 35000,
    }
    payload.update(overrides)
    response = client.post("/api/requests", json=payload)
    return response.json()["id"]


def _complete_observation(request_id, total_price=30000):
    return PriceObservation(
        request_id=request_id,
        status="complete",
        total_price=total_price,
        flight_status="complete",
        hotel_status="complete",
        cab_status="complete",
    )


def test_buy_now_books_the_current_price_with_no_notification_click(client, db, two_users):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    fresh_observation = _complete_observation(request_id, total_price=32000)
    db.add(fresh_observation)
    db.commit()
    db.refresh(fresh_observation)

    with patch("app.routers.booking.create_observation", return_value=fresh_observation):
        response = client.post(f"/api/requests/{request_id}/buy-now?user_id={user_a.id}")

    assert response.status_code == 200
    booking = response.json()
    assert booking["accepted_total"] == 32000
    assert booking["aggregate_status"] == "confirmed"


def test_buy_now_is_scoped_to_the_owning_user(client, db, two_users):
    """A real cross-user ownership check, not just a happy path - buying
    for someone else's request must 404, the same as every other
    request-scoped endpoint."""
    user_a, user_b = two_users
    request_id = _create_request(client, user_a.id)

    response = client.post(f"/api/requests/{request_id}/buy-now?user_id={user_b.id}")

    assert response.status_code == 404


def test_buy_now_refuses_an_incomplete_check(client, db, two_users):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    unavailable_observation = PriceObservation(request_id=request_id, status="unavailable")
    db.add(unavailable_observation)
    db.commit()
    db.refresh(unavailable_observation)

    with patch("app.routers.booking.create_observation", return_value=unavailable_observation):
        response = client.post(f"/api/requests/{request_id}/buy-now?user_id={user_a.id}")

    assert response.status_code == 400


def test_shock_and_check_moves_this_trips_own_market_and_returns_a_fresh_check(client, db, two_users):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)

    flight_row = SyntheticFlightOption(
        origin_code="BOM",
        destination_code="GOI",
        travel_date=date(2026, 12, 26),
        carrier_code="6E",
        carrier_name="IndiGo",
        flight_number=101,
        departure_time="10:00",
        arrival_time="12:00",
        stops=0,
        base_price_inr=5000.0,
        current_price_inr=5000.0,
    )
    db.add(flight_row)
    db.commit()
    db.refresh(flight_row)

    fresh_observation = _complete_observation(request_id, total_price=40000)
    db.add(fresh_observation)
    db.commit()
    db.refresh(fresh_observation)
    with patch("app.routers.lab.create_observation", return_value=fresh_observation):
        response = client.post(
            "/api/lab/shock-and-check", json={"request_id": request_id, "shock_fraction": 0.3}
        )

    assert response.status_code == 200
    assert response.json()["total_price"] == 40000

    db.refresh(flight_row)
    assert flight_row.current_price_inr == 6500.0


def test_shock_and_check_clamps_an_out_of_range_fraction(client, db, two_users):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)

    flight_row = SyntheticFlightOption(
        origin_code="BOM",
        destination_code="GOI",
        travel_date=date(2026, 12, 26),
        carrier_code="6E",
        carrier_name="IndiGo",
        flight_number=101,
        departure_time="10:00",
        arrival_time="12:00",
        stops=0,
        base_price_inr=5000.0,
        current_price_inr=5000.0,
    )
    db.add(flight_row)
    db.commit()
    db.refresh(flight_row)

    fresh_observation = _complete_observation(request_id, total_price=10000)
    db.add(fresh_observation)
    db.commit()
    db.refresh(fresh_observation)
    with patch("app.routers.lab.create_observation", return_value=fresh_observation):
        response = client.post(
            "/api/lab/shock-and-check", json={"request_id": request_id, "shock_fraction": 5.0}
        )

    assert response.status_code == 200
    db.refresh(flight_row)
    # Clamped to MANUAL_SHOCK_MAX_FRACTION (0.60), not the raw 5.0 requested.
    assert flight_row.current_price_inr == 8000.0
