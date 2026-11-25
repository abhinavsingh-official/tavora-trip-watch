"""Pricing engine - every endpoint that needs a price goes through here. Sums an itemized total and
tags the package complete/provisional/unavailable; only "complete" can trigger a budget alert."""

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.sim_controller import sim_controller
from app.sources import cabs, flights, hotels

# Placeholder rate; no source exposes a real tax schedule
TAX_RATE = 0.05

# Placeholder per-adult, per-leg checked-bag fee (no real airline fee schedule available)
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
    # Real call is skipped entirely when an override is active; return leg is zeroed, not added to a fetched fare
    override = sim_controller.pop_override(trip_request.id, "flight")
    if override is not None:
        return {"outbound_price": override, "return_price": 0.0, "status": "complete", "raw": None}
    return flights.get_flight_prices(trip_request, db)


def _effective_hotel(trip_request, db: Session) -> dict:
    override = sim_controller.pop_override(trip_request.id, "hotel")
    if override is not None:
        return {"price": override, "status": "complete", "raw": None}
    return hotels.get_hotel_price(trip_request, db)


def _effective_cab(trip_request, db: Session) -> dict:
    override = sim_controller.pop_override(trip_request.id, "cab")
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
            # Folded into taxes_fees (not subtotal) so itemized price fields still sum to total - taxes_fees
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
