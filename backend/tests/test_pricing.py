"""The price-adding-up math (Sec. 05) - the single thing most likely to
silently break without anyone noticing, since a wrong total still "looks
like a number." Mocks the three source modules so this tests pricing.py's
own logic, not real Sabre/Hotelbeds calls.
"""

from unittest.mock import patch

from app.models import TripRequest, User
from app.pricing import TAX_RATE, build_package
from app.sim_controller import sim_controller


def _make_request(db, **overrides):
    user = User(name="Pricing Test User")
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
    )
    defaults.update(overrides)
    trip_request = TripRequest(**defaults)
    db.add(trip_request)
    db.commit()
    db.refresh(trip_request)
    return trip_request


def test_itemized_total_adds_up_every_component(db):
    trip_request = _make_request(db)

    with (
        patch(
            "app.pricing.flights.get_flight_prices",
            return_value={
                "outbound_price": 7000.0,
                "return_price": 6000.0,
                "status": "complete",
                "raw": None,
            },
        ),
        patch(
            "app.pricing.hotels.get_hotel_price",
            return_value={"price": 15000.0, "status": "complete", "raw": None},
        ),
        patch(
            "app.pricing.cabs.get_cab_prices",
            return_value={
                "outbound_price": 900.0,
                "return_price": 900.0,
                "status": "complete",
                "raw": None,
            },
        ),
    ):
        package = build_package(trip_request)

    subtotal = 7000.0 + 6000.0 + 15000.0 + 900.0 + 900.0
    expected_tax = round(subtotal * TAX_RATE, 2)
    assert package.taxes_fees == expected_tax
    assert package.total_price == round(subtotal + expected_tax, 2)
    assert package.status == "complete"
    # Nothing silently dropped - every component individually present too.
    assert package.flight_outbound_price == 7000.0
    assert package.flight_return_price == 6000.0
    assert package.hotel_total_price == 15000.0
    assert package.cab_outbound_price == 900.0
    assert package.cab_return_price == 900.0


def test_any_unavailable_component_makes_the_whole_package_unavailable(db):
    trip_request = _make_request(db)

    with (
        patch(
            "app.pricing.flights.get_flight_prices",
            return_value={"outbound_price": None, "return_price": None, "status": "unavailable", "raw": None},
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
        package = build_package(trip_request)

    # A missing required price must never silently become zero (Sec. 05) -
    # the whole package is unavailable, with no total at all, not a total
    # that quietly excludes the missing piece.
    assert package.status == "unavailable"
    assert package.total_price is None
    assert package.taxes_fees is None


def test_flight_override_replaces_the_whole_component_not_just_outbound(db):
    # Regression test for a real bug caught during manual testing: an
    # override used to only replace the outbound leg, leaving the real
    # return-leg price silently stacked on top of it.
    trip_request = _make_request(db)
    sim_controller.set_override(trip_request.id, "flight", 1000.0)
    try:
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
            package = build_package(trip_request)

        assert package.flight_outbound_price == 1000.0
        assert package.flight_return_price == 0.0
        subtotal = 1000.0 + 0.0 + 15000.0 + 900.0 + 900.0
        assert package.total_price == round(subtotal * (1 + TAX_RATE), 2)
    finally:
        sim_controller.reset()


def test_override_is_deterministic_even_when_the_real_supplier_call_would_fail(db):
    # Audit finding #6: an override used to only replace the *price*,
    # computed after still making the real call - if the real call failed
    # at the same moment (confirmed to happen in practice with Hotelbeds),
    # the whole package still came back "unavailable" and the override did
    # nothing. Proves the real call is never even made once an override is
    # set, and the package is always "complete" regardless of what the real
    # source would have said.
    trip_request = _make_request(db)
    sim_controller.set_override(trip_request.id, "hotel", 12000.0)
    try:
        with (
            patch("app.pricing.flights.get_flight_prices") as mock_flights,
            patch("app.pricing.hotels.get_hotel_price") as mock_hotels,
            patch(
                "app.pricing.cabs.get_cab_prices",
                return_value={"outbound_price": 900.0, "return_price": 900.0, "status": "complete", "raw": None},
            ),
        ):
            mock_flights.return_value = {
                "outbound_price": 7000.0,
                "return_price": 6000.0,
                "status": "complete",
                "raw": None,
            }
            package = build_package(trip_request)

        mock_hotels.assert_not_called()
        assert package.hotel_total_price == 12000.0
        assert package.hotel_status == "complete"
        assert package.status == "complete"
        assert package.total_price is not None
    finally:
        sim_controller.reset()
