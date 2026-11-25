"""Known-issue fix: the spec wants the flight/hotel/cab holds timed independently instead of one
shared 2-minute timer for the whole trip (see monitoring.py's COMPONENT_HOLD_MINUTES). Covers both
the duration math itself and that book() can reject on one specific component's expiry without
needing all three to have lapsed."""

from datetime import timedelta

from app.models import Notification, PriceObservation
from app.monitoring import COMPONENT_HOLD_MINUTES, expired_components, set_component_holds
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
    notification = Notification(request_id=request_id, observation_id=observation.id, held_observation_id=observation.id)
    set_component_holds(notification, sim_clock.get_now(simulated=False))
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def test_set_component_holds_gives_each_component_its_own_duration():
    notification = Notification()
    now = sim_clock.get_now(simulated=False)
    set_component_holds(notification, now)

    assert notification.held_until_flight == now + timedelta(minutes=COMPONENT_HOLD_MINUTES["flight"])
    assert notification.held_until_hotel == now + timedelta(minutes=COMPONENT_HOLD_MINUTES["hotel"])
    assert notification.held_until_cab == now + timedelta(minutes=COMPONENT_HOLD_MINUTES["cab"])
    # Not one shared timer - the three deadlines are genuinely different instants
    assert len({notification.held_until_flight, notification.held_until_hotel, notification.held_until_cab}) == 3


def test_expired_components_blames_only_the_one_component_past_its_own_hold():
    notification = Notification()
    now = sim_clock.get_now(simulated=False)
    set_component_holds(notification, now)

    # Flight's hold (2 min) has lapsed; hotel's (3 min) and cab's (5 min) haven't
    check_at = now + timedelta(minutes=2, seconds=30)
    assert expired_components(notification, check_at) == ["flight"]


def test_book_rejects_with_only_flights_hold_expired(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    notification = _held_notification(db, request_id)

    notification.held_until_flight = sim_clock.get_now(simulated=False) - timedelta(seconds=1)
    db.commit()

    response = client.post(
        f"/api/requests/{request_id}/book?user_id={user_a.id}",
        json={"notification_id": notification.id},
    )
    assert response.status_code == 409
    assert "flight" in response.json()["detail"]
