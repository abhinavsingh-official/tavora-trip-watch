"""Real bug reported live: a request's very first (oldest, worst) notification kept showing up in
the bell forever, even after later re-alerts had already superseded it with a much better price -
`list_notifications` ordered oldest-first and returned every historical notification for a request,
so the stale high number was what a reviewer actually saw. Only the latest notification per request
is the live opportunity; older ones are moot once a further drop has already re-alerted over them."""

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


def _notification(db, request_id, total_price):
    observation = PriceObservation(request_id=request_id, status="complete", total_price=total_price)
    db.add(observation)
    db.commit()
    db.refresh(observation)
    notification = Notification(request_id=request_id, observation_id=observation.id)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def test_only_the_latest_notification_per_request_is_listed(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)

    stale = _notification(db, request_id, 34559.65)
    latest = _notification(db, request_id, 21184.10)
    assert latest.id > stale.id

    response = client.get(f"/api/notifications?user_id={user_a.id}")
    assert response.status_code == 200
    body = response.json()

    assert len(body) == 1
    assert body[0]["id"] == latest.id
    assert body[0]["total_price"] == 21184.10


def test_notifications_across_different_requests_are_each_kept(client, two_users, db):
    user_a, _ = two_users
    request_a = _create_request(client, user_a.id)
    request_b = _create_request(client, user_a.id)

    notif_a = _notification(db, request_a, 30000.0)
    notif_b = _notification(db, request_b, 20000.0)

    response = client.get(f"/api/notifications?user_id={user_a.id}")
    ids = {row["id"] for row in response.json()}
    assert ids == {notif_a.id, notif_b.id}


def test_most_recently_alerted_request_is_listed_first(client, two_users, db):
    user_a, _ = two_users
    request_a = _create_request(client, user_a.id)
    request_b = _create_request(client, user_a.id)

    _notification(db, request_a, 30000.0)
    second = _notification(db, request_b, 20000.0)

    response = client.get(f"/api/notifications?user_id={user_a.id}")
    body = response.json()
    assert body[0]["id"] == second.id
