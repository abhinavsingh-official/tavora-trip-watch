from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BookingAttempt, SharedRoomPool, SimulationLogEntry, TripRequest
from app.monitoring import create_observation
from app.price_mutation import apply_manual_shock, mutate_all_prices
from app.routers.booking import buy_now
from app.scheduler import run_one_cycle
from app.schemas import (
    BookingAttemptOut,
    LabAdvanceClockIn,
    LabBookNowIn,
    LabCancelFailureIn,
    LabClockOut,
    LabFailComponentIn,
    LabOverrideIn,
    LabPriceCheckTimeoutIn,
    LabRestartAfterIn,
    LabShockIn,
    LabSharedRoomScenarioIn,
    LabTriggerCycleOut,
    PriceObservationOut,
    SharedRoomRaceEntryOut,
    SharedRoomStatusOut,
)
from app.sim_clock import sim_clock
from app.sim_controller import sim_controller
from app.simulation_log import log_event

"""Simulation - dev/demo only, never hit by real user-facing screens."""
router = APIRouter(prefix="/api/lab", tags=["lab"])


def _get_request_or_404(request_id: int, db: Session) -> TripRequest:
    trip_request = db.query(TripRequest).filter(TripRequest.id == request_id).first()
    if trip_request is None:
        raise HTTPException(status_code=404, detail="Request not found")
    return trip_request


@router.get("/clock", response_model=LabClockOut)
def get_clock():
    return LabClockOut(now=sim_clock.get_now(simulated=True))


@router.post("/clock/advance", response_model=LabClockOut)
def advance_clock(payload: LabAdvanceClockIn, db: Session = Depends(get_db)):
    """Lets us fast-forward past a 2-minute hold in seconds instead of waiting for real time."""
    sim_clock.advance(payload.minutes)
    log_event(
        db,
        event_type="lab_clock_advance",
        summary=f"Advanced the simulated clock by {payload.minutes} minute(s)",
        status="info",
    )
    return LabClockOut(now=sim_clock.get_now(simulated=True))


@router.post("/override")
def set_override(payload: LabOverrideIn, db: Session = Depends(get_db)):
    trip_request = _get_request_or_404(payload.request_id, db)
    sim_controller.set_override(payload.request_id, payload.component, payload.price)
    log_event(
        db,
        event_type="lab_override",
        trip_request=trip_request,
        summary=f"Forced the {payload.component} price to ₹{payload.price} for the next check",
        status="info",
    )
    return {"ok": True}


@router.post("/fail-component")
def fail_component(payload: LabFailComponentIn, db: Session = Depends(get_db)):
    # One-shot: "fail"/"unavailable" stop and compensate; "timeout" leaves it "unknown" until reconcile resolves it
    trip_request = _get_request_or_404(payload.request_id, db)
    sim_controller.set_booking_failure(payload.request_id, payload.component, payload.outcome)
    log_event(
        db,
        event_type="lab_fail_component",
        trip_request=trip_request,
        summary=f"Armed a forced '{payload.outcome}' outcome on the next {payload.component} booking attempt",
        status="info",
    )
    return {"ok": True}


@router.post("/cancel-failure")
def cancel_failure(payload: LabCancelFailureIn, db: Session = Depends(get_db)):
    """Forces the next compensating cancellation of this component to itself fail."""
    trip_request = _get_request_or_404(payload.request_id, db)
    sim_controller.set_cancel_failure(payload.request_id, payload.component)
    log_event(
        db,
        event_type="lab_cancel_failure",
        trip_request=trip_request,
        summary=f"Armed a forced compensating-cancellation failure on {payload.component}",
        status="info",
    )
    return {"ok": True}


@router.post("/price-check-timeout")
def set_price_check_timeout(payload: LabPriceCheckTimeoutIn, db: Session = Depends(get_db)):
    """Arms a supplier timeout for the next PRICE CHECK (not a booking attempt) on this component -
    the one real way to see 'provisional' fire: neither a complete price nor a confirmed unavailable."""
    trip_request = _get_request_or_404(payload.request_id, db)
    sim_controller.set_price_check_timeout(payload.request_id, payload.component)
    log_event(
        db,
        event_type="lab_price_check_timeout",
        trip_request=trip_request,
        summary=f"Armed a supplier timeout on the next {payload.component} price check",
        status="info",
    )
    return {"ok": True}


@router.post("/restart-after")
def restart_after(payload: LabRestartAfterIn, db: Session = Depends(get_db)):
    # Simulates a crash right after this component commits; a later attempt resumes from the next component
    trip_request = _get_request_or_404(payload.request_id, db)
    sim_controller.set_restart_after(payload.request_id, payload.component)
    log_event(
        db,
        event_type="lab_restart_after",
        trip_request=trip_request,
        summary=f"Armed a simulated restart right after {payload.component} confirms",
        status="info",
    )
    return {"ok": True}


@router.post("/book-now", response_model=BookingAttemptOut)
def book_now(payload: LabBookNowIn, db: Session = Depends(get_db)):
    # Same immediate buy_now every other page uses, so testing a failure/restart lever doesn't need a real alert first
    trip_request = _get_request_or_404(payload.request_id, db)
    return buy_now(trip_request.id, trip_request.user_id, db)


@router.post("/shock-and-check", response_model=PriceObservationOut)
def shock_and_check(payload: LabShockIn, db: Session = Depends(get_db)):
    # One slider drag, one effect: shocks this trip's market by an exact amount and checks the price in the same call
    trip_request = _get_request_or_404(payload.request_id, db)
    moved = apply_manual_shock(db, trip_request, payload.shock_fraction)
    observation = create_observation(trip_request, db)
    log_event(
        db,
        event_type="lab_shock",
        trip_request=trip_request,
        summary=(
            f"Shocked this trip's market by {payload.shock_fraction:+.0%} "
            f"({moved['flights_mutated']} flight option(s), {moved['hotels_mutated']} hotel option(s), "
            f"{moved['cabs_mutated']} cab option(s)) and re-checked - total now "
            + (f"₹{observation.total_price}" if observation.total_price is not None else "unavailable")
        ),
        total_cost_inr=observation.total_price,
        status="finished",
    )
    return observation


@router.post("/trigger-cycle", response_model=LabTriggerCycleOut)
def trigger_cycle(db: Session = Depends(get_db)):
    # Runs the same monitoring cycle the scheduler calls, on demand; prices only move every few cycles
    checked_ids = run_one_cycle()
    log_event(
        db,
        event_type="lab_trigger_cycle",
        summary=f"Triggered a monitoring cycle now - checked {len(checked_ids)} active request(s)",
        status="finished",
    )
    return LabTriggerCycleOut(checked_request_ids=checked_ids)


@router.post("/mutate-prices")
def mutate_prices(db: Session = Depends(get_db)):
    # Nudges prices without checking/alerting, unlike trigger-cycle which does both
    result = mutate_all_prices(db)
    log_event(
        db,
        event_type="lab_mutate_prices",
        summary=(
            f"Nudged prices: {result['flights_mutated']} flight option(s), "
            f"{result['cabs_mutated']} cab option(s), {result['hotels_mutated']} hotel option(s)"
        ),
        status="finished",
    )
    return {"ok": True, **result}


@router.post("/shared-room-scenario")
def set_shared_room_scenario(payload: LabSharedRoomScenarioIn, db: Session = Depends(get_db)):
    """See app/models.py's SharedRoomPool docstring for how this gets used."""
    db.query(SharedRoomPool).delete()
    # Clear any booking attempts left over from a previous race for these same requests,
    # so the status card doesn't show a stale confirmed/cancelled result from last time.
    db.query(BookingAttempt).filter(BookingAttempt.request_id.in_(payload.request_ids)).delete(
        synchronize_session=False
    )
    pool = SharedRoomPool(rooms_remaining=payload.rooms_remaining, request_ids=payload.request_ids)
    db.add(pool)
    db.commit()
    log_event(
        db,
        event_type="lab_shared_room_scenario",
        summary=(
            f"Set up a shared room pool ({payload.rooms_remaining} room(s)) for "
            f"requests {payload.request_ids} - next hotel-confirm race decides the winner"
        ),
        status="info",
    )
    return {"ok": True}


@router.get("/shared-room-scenario", response_model=SharedRoomStatusOut)
def get_shared_room_scenario(db: Session = Depends(get_db)):
    """
    So the race has a visible result, not just a setup confirmation: for
    each competing request, the latest booking attempt's hotel outcome -
    'confirmed' for whoever got the room, 'unavailable' for whoever lost
    the race, or null if that request hasn't tried to book yet.
    """
    pool = db.query(SharedRoomPool).order_by(SharedRoomPool.id.desc()).first()
    if pool is None:
        return SharedRoomStatusOut(rooms_remaining=0, entries=[])

    entries = []
    for request_id in pool.request_ids:
        trip_request = db.query(TripRequest).filter(TripRequest.id == request_id).first()
        if trip_request is None:
            continue
        latest_booking = (
            db.query(BookingAttempt)
            .filter(BookingAttempt.request_id == request_id)
            .order_by(BookingAttempt.created_at.desc())
            .first()
        )
        entries.append(
            SharedRoomRaceEntryOut(
                request_id=request_id,
                origin=trip_request.origin,
                destination=trip_request.destination,
                hotel_status=latest_booking.hotel_status if latest_booking else None,
                aggregate_status=latest_booking.aggregate_status if latest_booking else None,
            )
        )
    return SharedRoomStatusOut(rooms_remaining=pool.rooms_remaining, entries=entries)


@router.get("/log")
def list_log(limit: int = 100, offset: int = 0, db: Session = Depends(get_db)):
    # Scoped to the Scenario user plus untied global entries, or every active request's 5-min check would show up too
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    entries = (
        db.query(SimulationLogEntry)
        .filter(
            (SimulationLogEntry.user_name == "Scenario") | (SimulationLogEntry.user_name.is_(None))
        )
        .order_by(SimulationLogEntry.created_at.desc(), SimulationLogEntry.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [
        {
            "id": e.id,
            "created_at": e.created_at,
            "user_name": e.user_name,
            "route_label": e.route_label,
            "event_type": e.event_type,
            "summary": e.summary,
            "flight_name": e.flight_name,
            "hotel_name": e.hotel_name,
            "cab_name": e.cab_name,
            "total_cost_inr": e.total_cost_inr,
            "is_simulated": e.is_simulated,
            "status": e.status,
            "duration_ms": e.duration_ms,
        }
        for e in entries
    ]


@router.post("/log/clear")
def clear_log(db: Session = Depends(get_db)):
    """Same scope as list_log - never deletes real audit history for someone else's requests."""
    count = (
        db.query(SimulationLogEntry)
        .filter(
            (SimulationLogEntry.user_name == "Scenario") | (SimulationLogEntry.user_name.is_(None))
        )
        .delete(synchronize_session=False)
    )
    db.commit()
    return {"ok": True, "cleared": count}


@router.post("/reset")
def reset_lab(db: Session = Depends(get_db)):
    sim_controller.reset()
    sim_clock.reset()
    db.query(SharedRoomPool).delete()
    db.commit()
    log_event(
        db,
        event_type="lab_reset",
        summary="Simulation reset: clock, overrides, forced outcomes, and the shared-room pool cleared",
        status="info",
    )
    return {"ok": True}
