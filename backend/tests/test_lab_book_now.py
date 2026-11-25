"""
"Book now" collapses the real alert -> review -> hold -> pay dance into
one click for Simulation purposes - a reviewer scheduling a booking
failure shouldn't have to separately chase a real below-budget alert
first. create_observation is mocked (real supplier call); everything
after that - the notification, the hold, the actual booking attempt and
the scheduled failure taking effect - is real.
"""

from unittest.mock import patch

from app.models import PriceObservation


def _create_request(client, user_id):
    response = client.post(
        "/api/requests",
        json={
            "user_id": user_id,
            "origin": "Mumbai",
            "destination": "Goa",
            "outbound_date": "2026-12-26",
            "return_date": "2026-12-29",
            "adults": 2,
            "rooms": 1,
            "budget_inr": 35000,
        },
    )
    return response.json()["id"]


def test_book_now_checks_and_books_in_one_call(client, db, two_users):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)

    fresh_observation = PriceObservation(
        request_id=request_id,
        status="complete",
        total_price=30000,
        flight_status="complete",
        hotel_status="complete",
        cab_status="complete",
    )
    db.add(fresh_observation)
    db.commit()
    db.refresh(fresh_observation)

    with patch("app.routers.booking.create_observation", return_value=fresh_observation):
        response = client.post("/api/lab/book-now", json={"request_id": request_id})

    assert response.status_code == 200
    booking = response.json()
    assert booking["accepted_total"] == 30000
    assert booking["aggregate_status"] == "confirmed"
    assert booking["flight_status"] == "confirmed"
    assert booking["hotel_status"] == "confirmed"
    assert booking["cab_status"] == "confirmed"


def test_book_now_enacts_a_scheduled_failure_immediately(client, db, two_users):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)

    client.post(
        "/api/lab/fail-component",
        json={"request_id": request_id, "component": "hotel", "outcome": "fail"},
    )

    fresh_observation = PriceObservation(
        request_id=request_id,
        status="complete",
        total_price=30000,
        flight_status="complete",
        hotel_status="complete",
        cab_status="complete",
    )
    db.add(fresh_observation)
    db.commit()
    db.refresh(fresh_observation)

    with patch("app.routers.booking.create_observation", return_value=fresh_observation):
        response = client.post("/api/lab/book-now", json={"request_id": request_id})

    assert response.status_code == 200
    booking = response.json()
    assert booking["hotel_status"] == "failed"
    assert booking["flight_status"] == "cancelled"
    assert booking["aggregate_status"] == "partial"


def test_book_now_rejects_an_incomplete_check(client, db, two_users):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)

    unavailable_observation = PriceObservation(request_id=request_id, status="unavailable")
    db.add(unavailable_observation)
    db.commit()
    db.refresh(unavailable_observation)

    with patch("app.routers.booking.create_observation", return_value=unavailable_observation):
        response = client.post("/api/lab/book-now", json={"request_id": request_id})

    assert response.status_code == 400
