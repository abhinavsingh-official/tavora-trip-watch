"""Request-input validation (Sec. 05: "reject combinations that violate
[check-in/check-out] assumptions") - found missing by manually trying to
break the live app with a reversed date range (return before outbound),
9 adults/9 rooms: the hotel call came back honestly "unavailable", but
flight and cabs still priced a trip that can never happen, since nothing
ever checked the dates made sense.
"""

from app.models import TripRequest, User


def _base_payload(user_id, **overrides):
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
    return payload


def test_create_rejects_return_date_before_outbound(client, two_users):
    user_a, _ = two_users
    response = client.post(
        "/api/requests",
        json=_base_payload(user_a.id, outbound_date="2027-03-05", return_date="2026-12-04"),
    )
    assert response.status_code == 400


def test_create_rejects_return_date_equal_to_outbound(client, two_users):
    user_a, _ = two_users
    response = client.post(
        "/api/requests",
        json=_base_payload(user_a.id, outbound_date="2026-12-26", return_date="2026-12-26"),
    )
    assert response.status_code == 400


def test_create_rejects_zero_adults_or_rooms(client, two_users):
    user_a, _ = two_users
    assert client.post("/api/requests", json=_base_payload(user_a.id, adults=0)).status_code == 422
    assert client.post("/api/requests", json=_base_payload(user_a.id, rooms=0)).status_code == 422


def test_edit_rejects_a_return_date_before_the_existing_outbound_date(client, two_users):
    user_a, _ = two_users
    created = client.post("/api/requests", json=_base_payload(user_a.id))
    request_id = created.json()["id"]

    response = client.patch(
        f"/api/requests/{request_id}?user_id={user_a.id}",
        json={"return_date": "2026-12-01"},  # before the existing 2026-12-26 outbound
    )
    assert response.status_code == 400

    # The rejected edit must not have applied.
    unchanged = client.get(f"/api/requests/{request_id}?user_id={user_a.id}")
    assert unchanged.json()["return_date"] == "2026-12-29"


def test_check_rejects_a_request_that_was_already_invalid(client, two_users, db):
    """Simulates data that became invalid before this validation existed -
    inserted directly, bypassing the now-validated API, same as the real
    broken request found live."""
    user_a, _ = two_users
    trip_request = TripRequest(
        user_id=user_a.id,
        origin="Mumbai",
        destination="Goa",
        outbound_date="2027-03-05",
        return_date="2026-12-04",
        adults=9,
        rooms=9,
        budget_inr=200000,
    )
    db.add(trip_request)
    db.commit()
    db.refresh(trip_request)

    response = client.post(f"/api/requests/{trip_request.id}/check?user_id={user_a.id}")
    assert response.status_code == 400
