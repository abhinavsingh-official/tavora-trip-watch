"""Booking correctness: idempotency, and the Sec. 09 failure-table rows
added in V4 - inventory disappearing, a supplier timeout needing
reconciliation, a simulated restart mid-booking, and a failed compensating
cancellation. Each test drives the same Scenario Lab levers a reviewer would
use live, not a separate test-only code path.
"""

from datetime import timedelta

from app.models import Notification, PriceObservation
from app.sim_clock import sim_clock
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


def _held_notification(db, request_id, total_price=30000):
    observation = PriceObservation(request_id=request_id, status="complete", total_price=total_price)
    db.add(observation)
    db.commit()
    db.refresh(observation)
    held_until = sim_clock.get_now(simulated=False) + timedelta(minutes=2)
    notification = Notification(
        request_id=request_id,
        observation_id=observation.id,
        held_observation_id=observation.id,
        held_until_flight=held_until,
        held_until_hotel=held_until,
        held_until_cab=held_until,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def _book(client, request_id, notification_id, user_id):
    return client.post(
        f"/api/requests/{request_id}/book?user_id={user_id}",
        json={"notification_id": notification_id},
    )


def test_double_booking_the_same_notification_is_idempotent(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    notification = _held_notification(db, request_id)

    first = _book(client, request_id, notification.id, user_a.id)
    second = _book(client, request_id, notification.id, user_a.id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["aggregate_status"] == "confirmed"


def test_normal_booking_confirms_every_component(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    notification = _held_notification(db, request_id)

    response = _book(client, request_id, notification.id, user_a.id)
    body = response.json()

    assert body["aggregate_status"] == "confirmed"
    assert body["flight_status"] == body["hotel_status"] == body["cab_status"] == "confirmed"
    assert body["supplier_ref_flight"] and body["supplier_ref_hotel"] and body["supplier_ref_cab"]


def test_forced_unavailable_compensates_earlier_components(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    notification = _held_notification(db, request_id)

    sim_controller.set_booking_failure(request_id, "hotel", "unavailable")
    body = _book(client, request_id, notification.id, user_a.id).json()

    assert body["flight_status"] == "cancelled"
    assert body["hotel_status"] == "unavailable"
    assert body["cab_status"] == "pending"
    assert body["aggregate_status"] == "partial"
    sim_controller.reset()


def test_forced_timeout_needs_reconciliation_and_book_refuses_a_second_attempt(
    client, two_users, db
):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    notification = _held_notification(db, request_id)

    sim_controller.set_booking_failure(request_id, "hotel", "timeout")
    first = _book(client, request_id, notification.id, user_a.id).json()
    assert first["flight_status"] == "confirmed"
    assert first["hotel_status"] == "unknown"
    assert first["cab_status"] == "pending"
    assert first["aggregate_status"] == "needs_reconciliation"

    # A second call for the same notification must not create a new attempt
    # or silently re-run the component - it returns the same unresolved row.
    second = _book(client, request_id, notification.id, user_a.id).json()
    assert second["id"] == first["id"]
    assert second["aggregate_status"] == "needs_reconciliation"
    sim_controller.reset()


def test_reconcile_confirmed_resumes_the_remaining_components(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    notification = _held_notification(db, request_id)

    sim_controller.set_booking_failure(request_id, "hotel", "timeout")
    booking = _book(client, request_id, notification.id, user_a.id).json()

    response = client.post(
        f"/api/bookings/{booking['id']}/reconcile?user_id={user_a.id}",
        json={"outcome": "confirmed"},
    )
    body = response.json()
    assert response.status_code == 200
    assert body["hotel_status"] == "confirmed"
    assert body["cab_status"] == "confirmed"
    assert body["aggregate_status"] == "confirmed"
    sim_controller.reset()


def test_reconcile_failed_compensates_what_booked_before_it(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    notification = _held_notification(db, request_id)

    sim_controller.set_booking_failure(request_id, "hotel", "timeout")
    booking = _book(client, request_id, notification.id, user_a.id).json()

    response = client.post(
        f"/api/bookings/{booking['id']}/reconcile?user_id={user_a.id}",
        json={"outcome": "failed"},
    )
    body = response.json()
    assert body["flight_status"] == "cancelled"
    assert body["hotel_status"] == "failed"
    assert body["cab_status"] == "pending"
    assert body["aggregate_status"] == "partial"
    sim_controller.reset()


def test_restart_after_resumes_without_duplicating_the_booking_row(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    notification = _held_notification(db, request_id)

    sim_controller.set_restart_after(request_id, "flight")
    first = _book(client, request_id, notification.id, user_a.id).json()
    assert first["flight_status"] == "confirmed"
    assert first["hotel_status"] == "pending"
    assert first["aggregate_status"] == "in_progress"

    # The "restart" itself is just calling book() again - no lab lever left
    # to consume, since it was popped on the first call.
    second = _book(client, request_id, notification.id, user_a.id).json()
    assert second["id"] == first["id"]
    assert second["hotel_status"] == "confirmed"
    assert second["cab_status"] == "confirmed"
    assert second["aggregate_status"] == "confirmed"
    sim_controller.reset()


def test_cancellation_failure_flags_manual_intervention_without_losing_the_ref(
    client, two_users, db
):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    notification = _held_notification(db, request_id)

    sim_controller.set_booking_failure(request_id, "hotel", "fail")
    sim_controller.set_cancel_failure(request_id, "flight")
    body = _book(client, request_id, notification.id, user_a.id).json()

    assert body["flight_status"] == "cancellation_failed"
    assert body["supplier_ref_flight"] is not None  # never erased, just flagged
    assert body["hotel_status"] == "failed"
    assert body["aggregate_status"] == "manual_intervention"
    sim_controller.reset()


def test_booking_rejected_without_a_held_offer(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    observation = PriceObservation(request_id=request_id, status="complete", total_price=30000)
    db.add(observation)
    db.commit()
    db.refresh(observation)
    notification = Notification(request_id=request_id, observation_id=observation.id)
    db.add(notification)
    db.commit()
    db.refresh(notification)

    response = _book(client, request_id, notification.id, user_a.id)
    assert response.status_code == 400


def test_booking_rejected_after_hold_expires(client, two_users, db):
    # A real user's holds run on real wall-clock time, not the Simulation sandbox's clock (see
    # test_sim_clock.py) - so the expiry here is set directly in the past, not via sim_clock.advance().
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    notification = _held_notification(db, request_id)
    notification.held_until_flight = sim_clock.get_now(simulated=False) - timedelta(minutes=1)
    db.commit()

    response = _book(client, request_id, notification.id, user_a.id)
    assert response.status_code == 409


def test_fast_forwarding_the_simulation_clock_does_not_expire_a_real_users_hold(client, two_users, db):
    """Known-issue fix: Simulation's Clock lever used to shift time for every user. Advancing it now
    must not touch a real user's (A/B/C) still-fresh hold at all."""
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    notification = _held_notification(db, request_id)

    sim_clock.advance(10)  # far past every component's hold, but only for the Simulation sandbox
    try:
        response = _book(client, request_id, notification.id, user_a.id)
        assert response.status_code == 200
    finally:
        sim_clock.reset()
