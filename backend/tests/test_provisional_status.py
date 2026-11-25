"""Known-issue fix: "provisional" existed in the schema and the log/alert code paths (see
monitoring.py's log_event status mapping) but every real price check only ever came back "complete"
or "unavailable" - provisional never actually fired. A price-check timeout (distinct from a booking
timeout) on exactly one component now produces it for real, via the Lab's /price-check-timeout lever."""

from app.models import TripRequest
from app.pricing import build_package
from app.sim_controller import sim_controller


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
    assert response.status_code == 200
    return response.json()["id"]


def test_a_timed_out_component_alone_makes_the_package_provisional_not_unavailable(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)

    sim_controller.set_override(request_id, "flight", 10000)
    sim_controller.set_override(request_id, "cab", 2000)
    sim_controller.set_price_check_timeout(request_id, "hotel")

    trip_request_row = db.query(TripRequest).filter(TripRequest.id == request_id).first()
    package = build_package(trip_request_row, db)

    assert package.hotel_status == "timeout"
    assert package.flight_status == "complete"
    assert package.cab_status == "complete"
    assert package.status == "provisional"


def test_armed_price_check_timeout_is_one_shot(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    sim_controller.set_override(request_id, "flight", 10000)
    sim_controller.set_override(request_id, "cab", 2000)
    sim_controller.set_price_check_timeout(request_id, "hotel")

    assert sim_controller.pop_price_check_timeout(request_id, "hotel") is True
    assert sim_controller.pop_price_check_timeout(request_id, "hotel") is False


def test_lab_endpoint_arms_a_price_check_timeout(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)

    response = client.post(
        "/api/lab/price-check-timeout",
        json={"request_id": request_id, "component": "flight"},
    )
    assert response.status_code == 200
    assert sim_controller.pop_price_check_timeout(request_id, "flight") is True
