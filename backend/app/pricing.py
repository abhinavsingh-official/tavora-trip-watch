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

from sqlalchemy.orm import Session

from app.sim_controller import sim_controller
from app.sources import cabs, flights, hotels

"""A simple, documented flat rate standing in for taxes/mandatory charges
(Sec. 05) - not sourced from any supplier's real tax schedule, since none
of V1's sources expose one separately. Flagged here, not hidden.
"""
TAX_RATE = 0.05

"""
Sec. 05 lists "baggage requirements" as its own accounted-for item,
distinct from cab luggage capacity (which sources/cabs.py already
enforces as an eligibility rule). This is the flight side of it: a flat,
documented per-adult, per-leg checked-bag fee - not sourced from any real
airline's actual baggage fee schedule (none of this project's sources
expose one), applied only when the request actually asks for checked
baggage, same honesty as TAX_RATE above.
"""
CHECKED_BAGGAGE_FEE_PER_ADULT_PER_LEG = 500.0


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


def _effective_flight(trip_request, db: Session) -> dict:
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
    return flights.get_flight_prices(trip_request, db)


def _effective_hotel(trip_request, db: Session) -> dict:
    override = sim_controller.get_override(trip_request.id, "hotel")
    if override is not None:
        return {"price": override, "status": "complete", "raw": None}
    return hotels.get_hotel_price(trip_request, db)


def _effective_cab(trip_request, db: Session) -> dict:
    override = sim_controller.get_override(trip_request.id, "cab")
    if override is not None:
        return {"outbound_price": override, "return_price": 0.0, "status": "complete", "raw": None}
    return cabs.get_cab_prices(trip_request, db)


def build_package(trip_request, db: Session) -> PackageResult:
    flight = _effective_flight(trip_request, db)
    hotel = _effective_hotel(trip_request, db)
    cab = _effective_cab(trip_request, db)

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
        baggage_fee = 0.0
        if trip_request.checked_baggage:
            """Both legs - a checked bag is needed for the return flight
            too, not just the outbound one. Kept out of `subtotal` itself
            so the itemized flight/hotel/cab fields above still sum
            exactly to (total_price - taxes_fees); it's folded into
            taxes_fees instead, which already represents "taxes AND
            mandatory charges" collectively, not tax alone.
            """
            baggage_fee = 2 * trip_request.adults * CHECKED_BAGGAGE_FEE_PER_ADULT_PER_LEG
        taxes_fees = round(subtotal * TAX_RATE + baggage_fee, 2)
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
