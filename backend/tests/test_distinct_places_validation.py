"""
Same origin and destination isn't a real trip - there's nothing for the
monitoring to watch. Rejected at the request level, on create and edit,
same pattern as test_occupancy_validation.py.
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


def test_create_rejects_identical_origin_and_destination(client, two_users):
    user_a, _ = two_users
    response = client.post(
        "/api/requests", json=_base_payload(user_a.id, origin="Jaipur", destination="Jaipur")
    )
    assert response.status_code == 400
    assert "pick two different places" in response.json()["detail"]


def test_create_rejects_identical_places_case_insensitively(client, two_users):
    user_a, _ = two_users
    response = client.post(
        "/api/requests", json=_base_payload(user_a.id, origin="goa", destination="GOA")
    )
    assert response.status_code == 400


def test_edit_rejects_destination_matching_existing_origin(client, two_users):
    user_a, _ = two_users
    created = client.post("/api/requests", json=_base_payload(user_a.id)).json()

    response = client.patch(
        f"/api/requests/{created['id']}?user_id={user_a.id}", json={"destination": "Mumbai"}
    )

    assert response.status_code == 400
