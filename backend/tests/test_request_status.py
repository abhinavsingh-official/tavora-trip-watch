"""Audit finding #0: a paused or cancelled request could still be reviewed
and fully booked - reproduced live against a real running server before
being fixed here. These tests are the regression coverage that was missing
(finding #9) and let the bug ship undetected across five versions.

Held notifications are built directly (same pattern as test_booking.py),
not via a real `/review` call, so these stay fast and spend zero real
Sabre/Hotelbeds quota - the one test that needs a real review specifically
(proving the *rejected* review never reaches the real supplier call) checks
that directly instead.
"""

from datetime import timedelta

from app.models import Notification, PriceObservation
from app.sim_clock import sim_clock


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
    notification = Notification(
        request_id=request_id,
        observation_id=observation.id,
        held_observation_id=observation.id,
        held_until=sim_clock.get_now() + timedelta(minutes=2),
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def test_review_is_rejected_before_ever_touching_a_real_supplier(client, two_users, db):
    # No held fields set and no observation needed - if the status check
    # didn't come before create_observation, this would attempt a real
    # Sabre/Hotelbeds call and either hang or burn quota in CI.
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    client.post(f"/api/requests/{request_id}/cancel?user_id={user_a.id}")
    observation = PriceObservation(request_id=request_id, status="complete", total_price=30000)
    db.add(observation)
    db.commit()
    db.refresh(observation)
    notification = Notification(request_id=request_id, observation_id=observation.id)
    db.add(notification)
    db.commit()
    db.refresh(notification)

    response = client.post(f"/api/notifications/{notification.id}/review?user_id={user_a.id}")
    assert response.status_code == 400


def test_paused_request_cannot_be_reviewed(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    client.post(f"/api/requests/{request_id}/pause?user_id={user_a.id}")
    notification = _held_notification(db, request_id)

    response = client.post(f"/api/notifications/{notification.id}/review?user_id={user_a.id}")
    assert response.status_code == 400


def test_cancelled_request_cannot_be_booked_even_with_a_pre_existing_hold(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    notification = _held_notification(db, request_id)

    cancel_response = client.post(f"/api/requests/{request_id}/cancel?user_id={user_a.id}")
    assert cancel_response.status_code == 200

    book_response = client.post(
        f"/api/requests/{request_id}/book?user_id={user_a.id}",
        json={"notification_id": notification.id},
    )
    assert book_response.status_code == 400


def test_cancelling_clears_the_hold_the_booking_rejection_is_not_the_only_defense(
    client, two_users, db
):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    notification = _held_notification(db, request_id)
    assert notification.held_until is not None

    client.post(f"/api/requests/{request_id}/cancel?user_id={user_a.id}")

    db.refresh(notification)
    assert notification.held_until is None
    assert notification.held_observation_id is None


def test_cancelled_requests_notifications_are_not_listed(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    _held_notification(db, request_id)

    client.post(f"/api/requests/{request_id}/cancel?user_id={user_a.id}")

    response = client.get(f"/api/notifications?user_id={user_a.id}")
    assert response.json() == []


def test_cancelled_request_cannot_be_edited(client, two_users):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    client.post(f"/api/requests/{request_id}/cancel?user_id={user_a.id}")

    response = client.patch(
        f"/api/requests/{request_id}?user_id={user_a.id}", json={"budget_inr": 99999}
    )
    assert response.status_code == 400


def test_cancelled_request_can_be_restored_from_trash(client, two_users):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    client.post(f"/api/requests/{request_id}/cancel?user_id={user_a.id}")

    response = client.post(f"/api/requests/{request_id}/reactivate?user_id={user_a.id}")
    assert response.status_code == 200
    assert response.json()["status"] == "active"

    # and it's editable again now that it's back
    edit_response = client.patch(
        f"/api/requests/{request_id}?user_id={user_a.id}", json={"budget_inr": 40000}
    )
    assert edit_response.status_code == 200


def test_editing_a_request_bumps_its_updated_at(client, two_users):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    before = client.get(f"/api/requests/{request_id}?user_id={user_a.id}").json()["updated_at"]

    client.patch(f"/api/requests/{request_id}?user_id={user_a.id}", json={"budget_inr": 40000})

    after = client.get(f"/api/requests/{request_id}?user_id={user_a.id}").json()["updated_at"]
    assert after >= before
