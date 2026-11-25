"""Ownership scoping (Sec. 03: "requests, notifications and booking actions
must remain scoped to their owner") - automates the exact cross-user attempts
manually verified against a real running server during the post-V2 security
review, so this stays caught by every future change, not just the one time
it was checked by hand.
"""

from app.models import Notification, PriceObservation


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


def test_owner_can_read_their_own_request(client, two_users):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    response = client.get(f"/api/requests/{request_id}?user_id={user_a.id}")
    assert response.status_code == 200


def test_other_user_cannot_read_the_request(client, two_users):
    user_a, user_b = two_users
    request_id = _create_request(client, user_a.id)
    response = client.get(f"/api/requests/{request_id}?user_id={user_b.id}")
    assert response.status_code == 404


def test_other_user_cannot_check_price_on_someone_elses_request(client, two_users):
    user_a, user_b = two_users
    request_id = _create_request(client, user_a.id)
    response = client.post(f"/api/requests/{request_id}/check?user_id={user_b.id}")
    assert response.status_code == 404


def test_other_user_cannot_list_observations_on_someone_elses_request(client, two_users):
    user_a, user_b = two_users
    request_id = _create_request(client, user_a.id)
    response = client.get(f"/api/requests/{request_id}/observations?user_id={user_b.id}")
    assert response.status_code == 404


def test_other_user_cannot_review_someone_elses_notification(client, two_users, db):
    user_a, user_b = two_users
    request_id = _create_request(client, user_a.id)

    observation = PriceObservation(request_id=request_id, status="complete", total_price=100)
    db.add(observation)
    db.commit()
    db.refresh(observation)
    notification = Notification(request_id=request_id, observation_id=observation.id)
    db.add(notification)
    db.commit()
    db.refresh(notification)

    response = client.post(f"/api/notifications/{notification.id}/review?user_id={user_b.id}")
    assert response.status_code == 404


def test_other_user_cannot_book_someone_elses_notification(client, two_users, db):
    user_a, user_b = two_users
    request_id = _create_request(client, user_a.id)

    observation = PriceObservation(request_id=request_id, status="complete", total_price=100)
    db.add(observation)
    db.commit()
    db.refresh(observation)
    notification = Notification(request_id=request_id, observation_id=observation.id)
    db.add(notification)
    db.commit()
    db.refresh(notification)

    response = client.post(
        f"/api/requests/{request_id}/book?user_id={user_b.id}",
        json={"notification_id": notification.id},
    )
    assert response.status_code == 404


def test_other_user_cannot_edit_someone_elses_request(client, two_users):
    user_a, user_b = two_users
    request_id = _create_request(client, user_a.id)
    response = client.patch(
        f"/api/requests/{request_id}?user_id={user_b.id}", json={"budget_inr": 1}
    )
    assert response.status_code == 404

    # The rejected edit must not have applied - the owner's own budget is
    # exactly what it was created with, not silently changed to 1.
    owned_view = client.get(f"/api/requests/{request_id}?user_id={user_a.id}")
    assert owned_view.json()["budget_inr"] == 35000
