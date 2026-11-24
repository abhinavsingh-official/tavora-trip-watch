"""
The "Return to default" button: a request that's been edited/paused/
cancelled away from its original demo values should report
has_drifted_from_default=True, and resetting it should restore exactly
the seeded state.
"""

from app.models import User
from app.routers.requests import SEED_DEFAULTS


def _create_demo_request(db):
    """
    Mimics scripts/seed.py's request #1 exactly, including the ID -
    SEED_DEFAULTS is keyed by request_id, so the test needs the row to
    actually land at id=1 (a fresh test DB's first insert always does).
    """
    user = User(name="User A")
    db.add(user)
    db.commit()
    db.refresh(user)

    defaults = SEED_DEFAULTS[1]
    from app.models import TripRequest

    trip_request = TripRequest(user_id=user.id, **defaults)
    db.add(trip_request)
    db.commit()
    db.refresh(trip_request)
    assert trip_request.id == 1
    return user, trip_request


def test_unmodified_request_has_not_drifted(client, db):
    user, _ = _create_demo_request(db)

    response = client.get(f"/api/requests/1?user_id={user.id}")

    assert response.json()["has_drifted_from_default"] is False


def test_editing_a_field_marks_it_as_drifted(client, db):
    user, _ = _create_demo_request(db)

    client.patch(f"/api/requests/1?user_id={user.id}", json={"budget_inr": 99999})
    response = client.get(f"/api/requests/1?user_id={user.id}")

    assert response.json()["has_drifted_from_default"] is True
    assert response.json()["budget_inr"] == 99999.0


def test_cancelling_marks_it_as_drifted(client, db):
    user, _ = _create_demo_request(db)

    client.post(f"/api/requests/1/cancel?user_id={user.id}")
    response = client.get(f"/api/requests/1?user_id={user.id}")

    assert response.json()["has_drifted_from_default"] is True


def test_reset_restores_the_exact_seed_values(client, db):
    user, _ = _create_demo_request(db)
    client.patch(f"/api/requests/1?user_id={user.id}", json={"budget_inr": 99999, "adults": 10})
    client.post(f"/api/requests/1/cancel?user_id={user.id}")

    response = client.post(f"/api/requests/1/reset-to-default?user_id={user.id}")
    body = response.json()

    assert body["has_drifted_from_default"] is False
    assert body["budget_inr"] == 35000.0
    assert body["adults"] == 2
    assert body["status"] == "active"


def test_reset_is_404_for_a_request_with_no_known_default(client, db):
    """
    A fresh test DB's first insert lands at id=1, which SEED_DEFAULTS does
    define - burn ids 1-3 first so the real request under test lands
    outside the known-defaults range and genuinely exercises the 404 path.
    """
    user = User(name="Someone else")
    db.add(user)
    db.commit()
    db.refresh(user)
    for _ in range(3):
        client.post(
            "/api/requests",
            json={
                "user_id": user.id,
                "origin": "A",
                "destination": "B",
                "outbound_date": "2026-12-26",
                "return_date": "2026-12-29",
                "adults": 1,
                "rooms": 1,
                "budget_inr": 1000,
            },
        )

    response = client.post(
        "/api/requests",
        json={
            "user_id": user.id,
            "origin": "Chennai",
            "destination": "Kochi",
            "outbound_date": "2026-12-26",
            "return_date": "2026-12-29",
            "adults": 2,
            "rooms": 1,
            "budget_inr": 20000,
        },
    )
    new_request_id = response.json()["id"]

    reset_response = client.post(f"/api/requests/{new_request_id}/reset-to-default?user_id={user.id}")

    assert reset_response.status_code == 404
