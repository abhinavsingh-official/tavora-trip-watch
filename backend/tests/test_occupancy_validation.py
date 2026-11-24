"""
More rooms than adults isn't a real booking - confirmed live, it makes
Hotelbeds reject the real search with a 400 (splitting adults evenly
across rooms produces a 0-adult room). Rejected at the request level
instead, on create and edit.
"""


def _base_payload(user_id, **overrides):
    payload = dict(
        user_id=user_id,
        origin="Mumbai",
        destination="Goa",
        outbound_date="2026-12-26",
        return_date="2026-12-29",
        adults=2,
        rooms=1,
        budget_inr=35000,
    )
    payload.update(overrides)
    return payload


def test_create_rejects_more_rooms_than_adults(client, two_users):
    user_a, _ = two_users
    response = client.post("/api/requests", json=_base_payload(user_a.id, adults=2, rooms=3))
    assert response.status_code == 400
    assert "rooms can't exceed adults" in response.json()["detail"]


def test_create_allows_rooms_equal_to_adults(client, two_users):
    user_a, _ = two_users
    response = client.post("/api/requests", json=_base_payload(user_a.id, adults=2, rooms=2))
    assert response.status_code == 200


def test_edit_rejects_increasing_rooms_past_adults(client, two_users):
    user_a, _ = two_users
    created = client.post("/api/requests", json=_base_payload(user_a.id)).json()

    response = client.patch(
        f"/api/requests/{created['id']}?user_id={user_a.id}", json={"rooms": 5}
    )

    assert response.status_code == 400
