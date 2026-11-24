"""
component_names_from_raw has a real nesting gotcha: flights.py nests
outbound/return raw dicts one level deeper than hotels.py/cabs.py's flat
raw dicts (see app/sources/flights.py's get_flight_prices). A first pass
at this helper read the wrong level and always fell back to the generic
"Real Sabre fare (live fallback)" label even for genuinely synthetic
flights - this test is the regression guard for that.
"""

from app.models import User
from app.simulation_log import component_names_from_raw


def test_extracts_synthetic_flight_name_from_the_correctly_nested_raw_shape():
    raw_sources = {
        "flight": {
            "outbound": {"synthetic_carrier": "IndiGo", "synthetic_flight_number": 203},
            "return": {"synthetic_carrier": "Air India", "synthetic_flight_number": 512},
        },
        "hotel": {"cached_hotel_name": "Calangute Villae"},
        "cab": {"vendor_name": "CityLink Transfers", "vehicle_class": "Sedan"},
    }

    names = component_names_from_raw(raw_sources)

    assert names["flight_name"] == "IndiGo 203"
    assert names["hotel_name"] == "Calangute Villae"
    assert names["cab_name"] == "CityLink Transfers (Sedan)"


def test_falls_back_to_a_generic_label_for_a_real_live_sabre_response():
    raw_sources = {
        "flight": {"outbound": {"groupedItineraryResponse": {}}, "return": {"groupedItineraryResponse": {}}},
        "hotel": None,
        "cab": None,
    }

    names = component_names_from_raw(raw_sources)

    assert names["flight_name"] == "Real Sabre fare (live fallback)"
    assert names["hotel_name"] is None
    assert names["cab_name"] is None


def test_handles_missing_raw_sources_entirely():
    assert component_names_from_raw(None) == {"flight_name": None, "hotel_name": None, "cab_name": None}


def _create_request(client, user_id=1):
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
    return response.json()["id"]


def test_lab_actions_write_to_the_log_and_it_can_be_listed_and_cleared(client, db):
    """
    The log is scoped to the "Scenario" user (plus global, request-less
    entries) - see GET /api/lab/log - so this needs a real user by that
    name, not an arbitrary test user, to show up at all.
    """
    scenario_user = User(name="Scenario")
    db.add(scenario_user)
    db.commit()
    db.refresh(scenario_user)
    request_id = _create_request(client, user_id=scenario_user.id)

    override_response = client.post(
        "/api/lab/override", json={"request_id": request_id, "component": "hotel", "price": 5000.0}
    )
    assert override_response.status_code == 200

    log_response = client.get("/api/lab/log")
    assert log_response.status_code == 200
    entries = log_response.json()
    assert len(entries) >= 1
    assert entries[0]["event_type"] == "lab_override"
    assert "hotel" in entries[0]["summary"]

    clear_response = client.post("/api/lab/log/clear")
    assert clear_response.status_code == 200
    assert clear_response.json()["cleared"] >= 1

    assert client.get("/api/lab/log").json() == []


def test_log_excludes_events_from_a_real_non_scenario_user(client, two_users):
    """
    Confirms the fix for the actual reported confusion: a real user's own
    price check used to show up in the Simulation page's log too, mixed in
    with whatever scenario action was just run.
    """
    user_a, _ = two_users
    request_id = _create_request(client, user_id=user_a.id)

    override_response = client.post(
        "/api/lab/override", json={"request_id": request_id, "component": "hotel", "price": 5000.0}
    )
    assert override_response.status_code == 200

    entries = client.get("/api/lab/log").json()
    assert all(e["user_name"] != user_a.name for e in entries)
