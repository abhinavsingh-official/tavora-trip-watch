"""
New enforcement this session added to Sec. 05's own checklist: cab
passenger/luggage capacity rejection, flight max-stops filtering, and a
checked-baggage fee. All three previously existed only as stored,
never-read request fields - these tests are the proof they're now real.
"""

from unittest.mock import patch

from app.models import SyntheticCabOption, SyntheticFlightOption, TripRequest, User
from app.pricing import CHECKED_BAGGAGE_FEE_PER_ADULT_PER_LEG, build_package
from app.sources import cabs, flights


def _make_request(db, **overrides):
    user = User(name="Filtering Test User")
    db.add(user)
    db.commit()
    db.refresh(user)

    defaults = dict(
        user_id=user.id,
        origin="Mumbai",
        destination="Goa",
        outbound_date="2026-12-26",
        return_date="2026-12-29",
        adults=2,
        rooms=1,
        budget_inr=35000,
        max_stops_outbound=2,
        max_stops_return=2,
        checked_baggage=False,
    )
    defaults.update(overrides)
    trip_request = TripRequest(**defaults)
    db.add(trip_request)
    db.commit()
    db.refresh(trip_request)
    return trip_request


def _add_cab_option(db, **overrides):
    defaults = dict(
        vendor_name="Test Cabs",
        vehicle_class="Sedan",
        passenger_capacity=4,
        luggage_capacity=2,
        base_price_per_leg_inr=900.0,
        current_price_per_leg_inr=900.0,
    )
    defaults.update(overrides)
    option = SyntheticCabOption(**defaults)
    db.add(option)
    db.commit()
    return option


def test_cab_rejects_a_party_too_large_for_every_vehicle_class(db):
    _add_cab_option(db, passenger_capacity=4)
    trip_request = _make_request(db, adults=6)

    result = cabs.get_cab_prices(trip_request, db)

    assert result["status"] == "unavailable"
    assert result["outbound_price"] is None


def test_cab_rejects_checked_baggage_when_no_vehicle_has_enough_luggage_space(db):
    _add_cab_option(db, passenger_capacity=4, luggage_capacity=1)
    trip_request = _make_request(db, adults=4, checked_baggage=True)

    result = cabs.get_cab_prices(trip_request, db)

    # 4 adults with checked baggage need >= 4 luggage slots (1 per adult) -
    # the only available vehicle offers 1, so this must be unavailable, not
    # silently booked into something too small.
    assert result["status"] == "unavailable"


def test_cab_picks_the_cheapest_vehicle_that_actually_fits(db):
    _add_cab_option(db, vendor_name="Cheap But Small", passenger_capacity=2, luggage_capacity=1, current_price_per_leg_inr=500.0)
    _add_cab_option(db, vendor_name="Pricier But Fits", passenger_capacity=4, luggage_capacity=4, current_price_per_leg_inr=900.0)
    trip_request = _make_request(db, adults=4)

    result = cabs.get_cab_prices(trip_request, db)

    assert result["status"] == "complete"
    assert result["outbound_price"] == 900.0
    assert result["raw"]["vendor_name"] == "Pricier But Fits"


def _add_flight_option(db, **overrides):
    defaults = dict(
        origin_code="BOM",
        destination_code="GOI",
        travel_date="2026-12-26",
        carrier_code="6E",
        carrier_name="IndiGo",
        flight_number=101,
        departure_time="08:00",
        arrival_time="09:30",
        stops=0,
        base_price_inr=3700.0,
        current_price_inr=3700.0,
    )
    defaults.update(overrides)
    option = SyntheticFlightOption(**defaults)
    db.add(option)
    db.commit()
    return option


def test_flight_filters_out_options_exceeding_max_stops(db):
    _add_flight_option(db, flight_number=201, stops=0, current_price_inr=5000.0)
    _add_flight_option(db, flight_number=202, stops=2, current_price_inr=1000.0)
    trip_request = _make_request(db, max_stops_outbound=0)

    candidates = flights.get_flight_candidates(trip_request, db)

    # The cheaper 2-stop option must not even appear once it violates the
    # request's own max-stops constraint (Sec. 05: "reject combinations
    # that violate them") - not just be deprioritized.
    assert len(candidates["outbound"]) == 1
    assert candidates["outbound"][0]["flight_number"] == 201


def test_flight_price_scales_with_real_adult_count(db):
    _add_flight_option(db, travel_date="2026-12-26", current_price_inr=1000.0)
    # Departure after 11:45 - must clear the return-leg checkout + transfer
    # buffer rule (app/schedule_rules.py), unlike the default 08:00.
    _add_flight_option(
        db,
        travel_date="2026-12-29",
        origin_code="GOI",
        destination_code="BOM",
        departure_time="14:00",
        arrival_time="15:30",
        current_price_inr=900.0,
    )
    trip_request = _make_request(db, adults=3)

    result = flights.get_flight_prices(trip_request, db)

    assert result["outbound_price"] == 3000.0
    assert result["return_price"] == 2700.0


def test_outbound_flight_arriving_too_late_for_checkin_is_excluded(db):
    _add_flight_option(db, flight_number=301, departure_time="22:00", arrival_time="23:30", current_price_inr=500.0)
    _add_flight_option(db, flight_number=302, departure_time="08:00", arrival_time="09:30", current_price_inr=5000.0)
    trip_request = _make_request(db)

    candidates = flights.get_flight_candidates(trip_request, db)

    # The cheaper late-arrival option violates the check-in/transfer-buffer
    # assumption (app/schedule_rules.py) and must be excluded entirely.
    assert len(candidates["outbound"]) == 1
    assert candidates["outbound"][0]["flight_number"] == 302


def test_return_flight_departing_too_early_for_checkout_is_excluded(db):
    _add_flight_option(
        db,
        flight_number=401,
        origin_code="GOI",
        destination_code="BOM",
        travel_date="2026-12-29",
        departure_time="09:00",
        arrival_time="10:30",
        current_price_inr=500.0,
    )
    _add_flight_option(
        db,
        flight_number=402,
        origin_code="GOI",
        destination_code="BOM",
        travel_date="2026-12-29",
        departure_time="14:00",
        arrival_time="15:30",
        current_price_inr=5000.0,
    )
    trip_request = _make_request(db)

    candidates = flights.get_flight_candidates(trip_request, db)

    # The cheaper early-departure option can't realistically be made after
    # checkout (11:00) plus the transfer buffer - excluded entirely.
    assert len(candidates["return"]) == 1
    assert candidates["return"][0]["flight_number"] == 402


def test_checked_baggage_adds_a_flat_documented_fee_to_the_whole_package(db):
    """
    Hotel/flight/cab sources are mocked here (not real DB-backed
    candidates) specifically so this test never touches a real Hotelbeds
    call - same reasoning as test_pricing.py's existing mocked tests.
    """
    trip_request_with_bag = _make_request(db, checked_baggage=True)
    trip_request_without_bag = _make_request(db, checked_baggage=False)

    with (
        patch(
            "app.pricing.flights.get_flight_prices",
            return_value={"outbound_price": 7000.0, "return_price": 6000.0, "status": "complete", "raw": None},
        ),
        patch(
            "app.pricing.hotels.get_hotel_price",
            return_value={"price": 15000.0, "status": "complete", "raw": None},
        ),
        patch(
            "app.pricing.cabs.get_cab_prices",
            return_value={"outbound_price": 900.0, "return_price": 900.0, "status": "complete", "raw": None},
        ),
    ):
        with_bag = build_package(trip_request_with_bag, db)
        without_bag = build_package(trip_request_without_bag, db)

    expected_fee = 2 * trip_request_with_bag.adults * CHECKED_BAGGAGE_FEE_PER_ADULT_PER_LEG
    """Itemized component prices are identical either way - the fee lives
    only in taxes_fees, never silently inflating the flight/hotel/cab
    numbers themselves."""
    assert with_bag.flight_outbound_price == without_bag.flight_outbound_price
    assert with_bag.taxes_fees - without_bag.taxes_fees == round(expected_fee, 2)
    assert with_bag.total_price - without_bag.total_price == round(expected_fee, 2)
