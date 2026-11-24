from fastapi import APIRouter

from app.scheduler import run_one_cycle
from app.schemas import (
    LabAdvanceClockIn,
    LabCancelFailureIn,
    LabClockOut,
    LabFailComponentIn,
    LabOverrideIn,
    LabRestartAfterIn,
    LabTriggerCycleOut,
)
from app.sim_clock import sim_clock
from app.sim_controller import sim_controller

"""
Everything here is explicitly dev/demo-only - the Scenario Lab, never called
by the real user-facing screens. See docs/DECISIONS.md "Simulation design".
"""
router = APIRouter(prefix="/api/lab", tags=["lab"])


@router.get("/clock", response_model=LabClockOut)
def get_clock():
    return LabClockOut(now=sim_clock.get_now())


@router.post("/clock/advance", response_model=LabClockOut)
def advance_clock(payload: LabAdvanceClockIn):
    """
    The literal "replay without waiting for real market/time movements"
    requirement (Sec. 11) - fast-forwards past a 2-minute hold in seconds.
    """
    sim_clock.advance(payload.minutes)
    return LabClockOut(now=sim_clock.get_now())


@router.post("/override")
def set_override(payload: LabOverrideIn):
    sim_controller.set_override(payload.request_id, payload.component, payload.price)
    return {"ok": True}


@router.post("/fail-component")
def fail_component(payload: LabFailComponentIn):
    """
    Forces the NEXT booking attempt on this request to hit this outcome on
    this component - consumed (one-shot) by that attempt. "fail"/
    "unavailable" both stop and compensate; "timeout" leaves it "unknown"
    until /bookings/{id}/reconcile resolves it (Sec. 09 rows 2 and 4).
    """
    sim_controller.set_booking_failure(payload.request_id, payload.component, payload.outcome)
    return {"ok": True}


@router.post("/cancel-failure")
def cancel_failure(payload: LabCancelFailureIn):
    """
    Forces the NEXT compensating cancellation of this component (after a
    failure elsewhere in the same booking) to itself fail - Sec. 09 row 6.
    """
    sim_controller.set_cancel_failure(payload.request_id, payload.component)
    return {"ok": True}


@router.post("/restart-after")
def restart_after(payload: LabRestartAfterIn):
    """
    Forces the NEXT booking attempt on this request to stop right after
    this component commits, as if the process crashed there - Sec. 09 row
    5 / Sec. 11 scenario 6. A later booking attempt on the same
    notification resumes from the next component, not a new row.
    """
    sim_controller.set_restart_after(payload.request_id, payload.component)
    return {"ok": True}


@router.post("/trigger-cycle", response_model=LabTriggerCycleOut)
def trigger_cycle():
    """
    Runs the real monitoring cycle immediately instead of waiting up to 5
    real minutes for the scheduler - the same function the scheduler calls,
    not a separate demo-only code path.
    """
    return LabTriggerCycleOut(checked_request_ids=run_one_cycle())


@router.post("/reset")
def reset_lab():
    sim_controller.reset()
    sim_clock.reset()
    return {"ok": True}
