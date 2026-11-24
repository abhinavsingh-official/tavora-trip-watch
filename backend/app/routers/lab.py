from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import SharedRoomPool, SimulationLogEntry, TripRequest
from app.price_mutation import mutate_all_prices
from app.scheduler import run_one_cycle
from app.schemas import (
    LabAdvanceClockIn,
    LabCancelFailureIn,
    LabClockOut,
    LabFailComponentIn,
    LabOverrideIn,
    LabRestartAfterIn,
    LabSharedRoomScenarioIn,
    LabTriggerCycleOut,
)
from app.sim_clock import sim_clock
from app.sim_controller import sim_controller
from app.simulation_log import log_event

"""Scenario Lab - dev/demo only, never hit by real user-facing screens."""
router = APIRouter(prefix="/api/lab", tags=["lab"])


def _get_request_or_404(request_id: int, db: Session) -> TripRequest:
    trip_request = db.query(TripRequest).filter(TripRequest.id == request_id).first()
    if trip_request is None:
        raise HTTPException(status_code=404, detail="Request not found")
    return trip_request


@router.get("/clock", response_model=LabClockOut)
def get_clock():
    return LabClockOut(now=sim_clock.get_now())


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
    return LabClockOut(now=sim_clock.get_now())


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
    """
    Forces the next booking attempt on this request to hit this outcome on
    this component, then clears itself. "fail"/"unavailable" stop and
    compensate; "timeout" leaves it "unknown" until reconcile resolves it.
    """
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


@router.post("/restart-after")
def restart_after(payload: LabRestartAfterIn, db: Session = Depends(get_db)):
    """
    Forces the next booking attempt to stop right after this component
    commits, simulating a crash. A later attempt on the same notification
    resumes from the next component instead of starting over.
    """
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


@router.post("/trigger-cycle", response_model=LabTriggerCycleOut)
def trigger_cycle(db: Session = Depends(get_db)):
    """
    Runs the same monitoring cycle the scheduler calls, just on demand.
    run_one_cycle nudges prices itself before checking, so one click can
    produce a visible drop/alert.
    """
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
    """
    Nudges prices without checking/alerting, unlike trigger-cycle which
    does both. Lets a demo move prices a few times before triggering a
    check.
    """
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


@router.get("/log")
def list_log(limit: int = 100, db: Session = Depends(get_db)):
    entries = (
        db.query(SimulationLogEntry)
        .order_by(SimulationLogEntry.created_at.desc())
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
    count = db.query(SimulationLogEntry).delete()
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
        summary="Scenario Lab reset: clock, overrides, forced outcomes, and the shared-room pool cleared",
        status="info",
    )
    return {"ok": True}
