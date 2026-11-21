"""The pricing engine - every endpoint that needs a price goes through here.

Calls all three source modules, applies any active Scenario Lab override,
sums an itemized total, and tags the whole package complete/provisional/
unavailable. Only "complete" can ever trigger a budget alert (Sec. 05) -
V1's sources currently only ever produce "complete" or "unavailable" (see
sources/flights.py, sources/hotels.py), so "provisional" is schema-forward,
not yet reachable, until a real source returns genuinely partial data.
"""

from dataclasses import dataclass
from typing import Any

from app.sim_controller import sim_controller
from app.sources import cabs, flights, hotels

# A simple, documented flat rate standing in for taxes/mandatory charges
# (Sec. 05) - not sourced from any supplier's real tax schedule, since none
# of V1's sources expose one separately. Flagged here, not hidden.
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


def _apply_override(request_id: int, component: str, price: float | None) -> float | None:
    override = sim_controller.get_override(request_id, component)
    return override if override is not None else price


def build_package(trip_request) -> PackageResult:
    flight = flights.get_flight_prices(trip_request)
    hotel = hotels.get_hotel_price(trip_request)
    cab = cabs.get_cab_prices(trip_request)

    flight_outbound = _apply_override(trip_request.id, "flight", flight["outbound_price"])
    flight_return = flight["return_price"]  # override applies to the component, not per-leg
    hotel_total = _apply_override(trip_request.id, "hotel", hotel["price"])
    cab_outbound = _apply_override(trip_request.id, "cab", cab["outbound_price"])
    cab_return = cab["return_price"]

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
