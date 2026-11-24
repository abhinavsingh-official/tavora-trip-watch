"""
Sec. 11 scenario 4 - "last room contention": two users compete for the
same remaining room, at most one acquires it and books it. Nothing in the
real/synthetic hotel data had a shared, finite resource before this (each
request's hotel search is independent) - app/models.py's SharedRoomPool
and routers/booking.py's _try_claim_shared_room are the real mechanism;
this is the end-to-end proof it actually produces one winner and one
genuine rejection, not a crash or a double-grant.
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


def _book(client, request_id, notification_id, user_id):
    return client.post(
        f"/api/requests/{request_id}/book?user_id={user_id}",
        json={"notification_id": notification_id},
    )


def test_two_users_racing_for_one_room_produces_exactly_one_winner(client, two_users, db):
    user_a, user_b = two_users
    request_a = _create_request(client, user_a.id)
    request_b = _create_request(client, user_b.id)
    notification_a = _held_notification(db, request_a)
    notification_b = _held_notification(db, request_b)

    setup = client.post(
        "/api/lab/shared-room-scenario",
        json={"request_ids": [request_a, request_b], "rooms_remaining": 1},
    )
    assert setup.status_code == 200

    result_a = _book(client, request_a, notification_a.id, user_a.id).json()
    result_b = _book(client, request_b, notification_b.id, user_b.id).json()

    outcomes = {result_a["aggregate_status"], result_b["aggregate_status"]}
    # Exactly one request confirms everything; the other is left partial,
    # with its hotel component genuinely marked unavailable - not both
    # confirmed (a double-grant) and not both failing (an over-correction).
    assert outcomes == {"confirmed", "partial"}

    loser = result_a if result_a["aggregate_status"] == "partial" else result_b
    assert loser["hotel_status"] == "unavailable"


def test_a_request_not_in_any_pool_is_unaffected(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    notification = _held_notification(db, request_id)

    client.post("/api/lab/shared-room-scenario", json={"request_ids": [999999], "rooms_remaining": 0})

    body = _book(client, request_id, notification.id, user_a.id).json()

    assert body["aggregate_status"] == "confirmed"
