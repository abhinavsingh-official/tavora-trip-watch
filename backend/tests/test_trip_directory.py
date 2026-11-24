"""
"Your Bookings" reads /requests/{id}/directory, not the old /story
endpoint - the old one parses a stored observation's raw_sources, which
no longer holds a full candidate list once flights/hotels moved to the
synthetic/cached data layer (see docs/internal/decision-log.md). This
endpoint reads the live candidate tables directly instead, so it's
unaffected by that and always current.
"""

from app.models import SyntheticCabOption, SyntheticFlightOption, TripRequest, User


def test_directory_returns_the_cheapest_option_marked_selected(client, db):
    user = User(name="Directory Test User")
    db.add(user)
    db.commit()
    db.refresh(user)

    trip_request = TripRequest(
        user_id=user.id,
        origin="Mumbai",
        destination="Goa",
        outbound_date="2026-12-26",
        return_date="2026-12-29",
        adults=2,
        rooms=1,
        budget_inr=35000,
    )
    db.add(trip_request)
    db.commit()
    db.refresh(trip_request)

    db.add_all(
        [
            SyntheticFlightOption(
                origin_code="BOM", destination_code="GOI", travel_date="2026-12-26",
                carrier_code="6E", carrier_name="IndiGo", flight_number=101,
                departure_time="08:00", arrival_time="09:30", stops=0,
                base_price_inr=4000.0, current_price_inr=4000.0,
            ),
            SyntheticFlightOption(
                origin_code="BOM", destination_code="GOI", travel_date="2026-12-26",
                carrier_code="AI", carrier_name="Air India", flight_number=202,
                departure_time="10:00", arrival_time="11:30", stops=0,
                base_price_inr=3000.0, current_price_inr=3000.0,
            ),
            SyntheticCabOption(
                vendor_name="Test Cabs", vehicle_class="Sedan",
                passenger_capacity=4, luggage_capacity=2,
                base_price_per_leg_inr=900.0, current_price_per_leg_inr=900.0,
            ),
        ]
    )
    db.commit()

    response = client.get(f"/api/requests/{trip_request.id}/directory?user_id={user.id}")
    body = response.json()

    assert response.status_code == 200
    outbound = body["outbound_flight_candidates"]
    assert len(outbound) == 2
    cheapest = next(c for c in outbound if c["selected"])
    assert cheapest["price_inr"] == 3000.0 * 2  # 2 adults
    assert sum(1 for c in outbound if c["selected"]) == 1

    assert len(body["cab_candidates"]) == 1
    assert body["cab_candidates"][0]["selected"] is True


def test_directory_is_ownership_scoped(client, db):
    owner = User(name="Owner")
    intruder = User(name="Intruder")
    db.add_all([owner, intruder])
    db.commit()
    db.refresh(owner)
    db.refresh(intruder)

    trip_request = TripRequest(
        user_id=owner.id,
        origin="Mumbai",
        destination="Goa",
        outbound_date="2026-12-26",
        return_date="2026-12-29",
        adults=2,
        rooms=1,
        budget_inr=35000,
    )
    db.add(trip_request)
    db.commit()
    db.refresh(trip_request)

    response = client.get(f"/api/requests/{trip_request.id}/directory?user_id={intruder.id}")

    assert response.status_code == 404
