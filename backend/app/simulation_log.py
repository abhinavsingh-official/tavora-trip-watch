"""Writer side of the Simulation's activity log (see SimulationLogEntry in models.py)."""

from sqlalchemy.orm import Session

from app.models import SimulationLogEntry, TripRequest
from app.sim_clock import now_for_request, sim_clock


def _route_label(trip_request: TripRequest) -> str:
    return f"{trip_request.origin} -> {trip_request.destination}"


def _user_name(trip_request: TripRequest) -> str | None:
    return trip_request.user.name if trip_request.user is not None else None


def component_names_from_raw(raw_sources: dict | None) -> dict:
    """Pulls display names out of raw_sources; the live Sabre/Hotelbeds fallback has no name field, so those are
    labeled generically."""
    raw_sources = raw_sources or {}
    # flight's raw dict is nested per-leg under "flight"; hotel/cab are already flat
    flight_raw_by_leg = raw_sources.get("flight") or {}
    flight_raw = flight_raw_by_leg.get("outbound") or flight_raw_by_leg.get("return") or {}
    hotel_raw = raw_sources.get("hotel") or {}
    cab_raw = raw_sources.get("cab") or {}

    if flight_raw and "synthetic_carrier" in flight_raw:
        flight_name = f"{flight_raw['synthetic_carrier']} {flight_raw.get('synthetic_flight_number', '')}".strip()
    elif flight_raw:
        flight_name = "Real Sabre fare (live fallback)"
    else:
        flight_name = None

    if "cached_hotel_name" in hotel_raw:
        hotel_name = hotel_raw["cached_hotel_name"]
    elif hotel_raw:
        hotel_name = "Real Hotelbeds search (live fallback)"
    else:
        hotel_name = None

    if "vendor_name" in cab_raw:
        cab_name = f"{cab_raw['vendor_name']} ({cab_raw.get('vehicle_class', '')})".strip()
    else:
        cab_name = None

    return {"flight_name": flight_name, "hotel_name": hotel_name, "cab_name": cab_name}


def log_event(
    db: Session,
    *,
    event_type: str,
    summary: str,
    trip_request: TripRequest | None = None,
    flight_name: str | None = None,
    hotel_name: str | None = None,
    cab_name: str | None = None,
    total_cost_inr: float | None = None,
    is_simulated: bool = True,
    status: str = "info",
    duration_ms: int | None = None,
) -> SimulationLogEntry:
    entry = SimulationLogEntry(
        created_at=now_for_request(trip_request) if trip_request is not None else sim_clock.get_now(simulated=False),
        request_id=trip_request.id if trip_request is not None else None,
        user_name=_user_name(trip_request) if trip_request is not None else None,
        route_label=_route_label(trip_request) if trip_request is not None else None,
        event_type=event_type,
        summary=summary,
        flight_name=flight_name,
        hotel_name=hotel_name,
        cab_name=cab_name,
        total_cost_inr=total_cost_inr,
        is_simulated=is_simulated,
        status=status,
        duration_ms=duration_ms,
    )
    db.add(entry)
    db.commit()
    return entry
