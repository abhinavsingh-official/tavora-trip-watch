"""The pricing engine - every endpoint that needs a price goes through here.

Calls all three source modules - or, if a Scenario Lab override is active
for a component, skips its real call entirely and uses the override instead
(V7, audit finding #6: an override must be genuinely deterministic, not
just "usually works if the real supplier also happens to cooperate") - sums
an itemized total, and tags the whole package complete/provisional/
unavailable. Only "complete" can ever trigger a budget alert (Sec. 05) -
V1's sources currently only ever produce "complete" or "unavailable" (see
sources/flights.py, sources/hotels.py), so "provisional" is schema-forward,
not yet reachable, until a real source returns genuinely partial data.
"""

from dataclasses import dataclass
from typing import Any

from app.sim_controller import sim_controller
from app.sources import cabs, flights, hotels

"""A simple, documented flat rate standing in for taxes/mandatory charges
(Sec. 05) - not sourced from any supplier's real tax schedule, since none
of V1's sources expose one separately. Flagged here, not hidden.
"""
TAX_RATE = 0.05


@dataclass
class PackageResult:
    flight_outbound_price: float | None
    flight_return_price: float | None
    flight_status: str
    hotel_total_price: float | None
    hotel_status: str
    cab_outbound_price: float | None
    cab_return_price: float | None
    cab_status: str
    taxes_fees: float | None
    total_price: float | None
    status: str
    raw_sources: dict[str, Any]


def _effective_flight(trip_request) -> dict:
    """Audit finding #6: an override used to only replace the *price*,
    computed *after* still making the real call - if the real call
    happened to fail at the same moment (confirmed to happen in
    practice), the whole package came back "unavailable" regardless of
    the override, contradicting both the Lab's own description
    ("instead of calling the real supplier") and Sec. 11's "deterministic
    fixtures... without waiting for real market movements" requirement.
    An active override now skips the real call entirely - overrides are
    per-component, not per-leg (docs/versions/V1_MODULES.md): the
    override value replaces the whole component's contribution, with the
    return leg zeroed rather than adding on top of a real, un-overridden
    return-leg price that was never fetched.
    """
    override = sim_controller.get_override(trip_request.id, "flight")
    if override is not None:
        return {"outbound_price": override, "return_price": 0.0, "status": "complete", "raw": None}
    return flights.get_flight_prices(trip_request)


def _effective_hotel(trip_request) -> dict:
    override = sim_controller.get_override(trip_request.id, "hotel")
    if override is not None:
        return {"price": override, "status": "complete", "raw": None}
    return hotels.get_hotel_price(trip_request)


def _effective_cab(trip_request) -> dict:
    override = sim_controller.get_override(trip_request.id, "cab")
    if override is not None:
        return {"outbound_price": override, "return_price": 0.0, "status": "complete", "raw": None}
    return cabs.get_cab_prices(trip_request)


def build_package(trip_request) -> PackageResult:
    flight = _effective_flight(trip_request)
    hotel = _effective_hotel(trip_request)
    cab = _effective_cab(trip_request)

    flight_outbound, flight_return = flight["outbound_price"], flight["return_price"]
    hotel_total = hotel["price"]
    cab_outbound, cab_return = cab["outbound_price"], cab["return_price"]

    statuses = [flight["status"], hotel["status"], cab["status"]]
    if all(s == "complete" for s in statuses):
        package_status = "complete"
    elif any(s == "unavailable" for s in statuses):
        package_status = "unavailable"
    else:
        package_status = "provisional"

    taxes_fees = None
    total_price = None
    if package_status != "unavailable":
        component_prices = [
            p
            for p in (flight_outbound, flight_return, hotel_total, cab_outbound, cab_return)
            if p is not None
        ]
        subtotal = sum(component_prices)
        taxes_fees = round(subtotal * TAX_RATE, 2)
        total_price = round(subtotal + taxes_fees, 2)

    return PackageResult(
        flight_outbound_price=flight_outbound,
        flight_return_price=flight_return,
        flight_status=flight["status"],
        hotel_total_price=hotel_total,
        hotel_status=hotel["status"],
        cab_outbound_price=cab_outbound,
        cab_return_price=cab_return,
        cab_status=cab["status"],
        taxes_fees=taxes_fees,
        total_price=total_price,
        status=package_status,
        raw_sources={
            "flight": flight.get("raw"),
            "hotel": hotel.get("raw"),
            "cab": cab.get("raw"),
        },
    )
