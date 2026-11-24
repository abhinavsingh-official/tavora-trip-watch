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

"""
Everything here is explicitly dev/demo-only - the Scenario Lab, never called
by the real user-facing screens. See docs/internal/decision-log.md "Simulation design".
"""
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
    """
    The literal "replay without waiting for real market/time movements"
    requirement (Sec. 11) - fast-forwards past a 2-minute hold in seconds.
    """
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
    Forces the NEXT booking attempt on this request to hit this outcome on
    this component - consumed (one-shot) by that attempt. "fail"/
    "unavailable" both stop and compensate; "timeout" leaves it "unknown"
    until /bookings/{id}/reconcile resolves it (Sec. 09 rows 2 and 4).
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
    """
    Forces the NEXT compensating cancellation of this component (after a
    failure elsewhere in the same booking) to itself fail - Sec. 09 row 6.
    """
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
    Forces the NEXT booking attempt on this request to stop right after
    this component commits, as if the process crashed there - Sec. 09 row
    5 / Sec. 11 scenario 6. A later booking attempt on the same
    notification resumes from the next component, not a new row.
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
    Runs the real monitoring cycle immediately instead of waiting up to 5
    real minutes for the scheduler - the same function the scheduler calls,
    not a separate demo-only code path. This already nudges prices first
    (run_one_cycle does that itself, see scheduler.py), so a normal
    trigger-cycle click can already produce a visible drop/alert on its own.
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
    A separate, explicit nudge - distinct from trigger-cycle, which
    mutates AND immediately checks/alerts in one step. This lets a live
    demo move prices a few times first (e.g. to simulate several days
    passing) and only then trigger a check, instead of always doing both
    at once.
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
    """Sec. 11 scenario 4 - see app/models.py's SharedRoomPool docstring."""
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
