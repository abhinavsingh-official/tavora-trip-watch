"""Pagination for the lists that genuinely grow without bound over a long-lived request's life:
price-check history and the merged ops timeline (found by an explicit API-contract pagination
audit). Lists that stay small by construction in this app's own scope (users, requests,
notifications) deliberately aren't paginated - adding limit/offset there would be over-engineering."""

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
    assert response.status_code == 200
    return response.json()["id"]


def _add_observations(db, request_id, count):
    for i in range(count):
        db.add(PriceObservation(request_id=request_id, status="complete", total_price=30000 + i))
    db.commit()


def test_observations_default_to_a_bounded_page(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    _add_observations(db, request_id, 60)

    response = client.get(f"/api/requests/{request_id}/observations?user_id={user_a.id}")
    assert response.status_code == 200
    assert len(response.json()) == 50  # default limit


def test_observations_limit_and_offset_page_through_history(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    _add_observations(db, request_id, 10)

    first_page = client.get(
        f"/api/requests/{request_id}/observations?user_id={user_a.id}&limit=4&offset=0"
    ).json()
    second_page = client.get(
        f"/api/requests/{request_id}/observations?user_id={user_a.id}&limit=4&offset=4"
    ).json()

    assert len(first_page) == 4
    assert len(second_page) == 4
    assert {o["id"] for o in first_page}.isdisjoint({o["id"] for o in second_page})


def test_observations_limit_is_clamped_to_a_sane_maximum(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    _add_observations(db, request_id, 5)

    response = client.get(
        f"/api/requests/{request_id}/observations?user_id={user_a.id}&limit=100000"
    )
    assert response.status_code == 200
    assert len(response.json()) == 5  # clamped internally, but there are only 5 rows anyway


def test_timeline_defaults_to_the_most_recent_events(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    _add_observations(db, request_id, 150)  # well past the default limit of 100

    response = client.get(f"/api/ops/requests/{request_id}/timeline?user_id={user_a.id}")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 100


def test_timeline_offset_pages_further_into_the_past(client, two_users, db):
    user_a, _ = two_users
    request_id = _create_request(client, user_a.id)
    _add_observations(db, request_id, 20)

    recent = client.get(
        f"/api/ops/requests/{request_id}/timeline?user_id={user_a.id}&limit=5&offset=0"
    ).json()
    older = client.get(
        f"/api/ops/requests/{request_id}/timeline?user_id={user_a.id}&limit=5&offset=5"
    ).json()

    assert len(recent) == 5
    assert len(older) == 5
    # The offset page is strictly earlier than the first page
    assert max(e["at"] for e in older) <= min(e["at"] for e in recent)
