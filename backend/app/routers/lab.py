from fastapi import APIRouter

from app.scheduler import run_one_cycle
from app.schemas import (
    LabAdvanceClockIn,
    LabClockOut,
    LabFailComponentIn,
    LabOverrideIn,
    LabTriggerCycleOut,
)
from app.sim_clock import sim_clock
from app.sim_controller import sim_controller

# Everything here is explicitly dev/demo-only - the Scenario Lab, never called
# by the real user-facing screens. See docs/DECISIONS.md "Simulation design".
router = APIRouter(prefix="/api/lab", tags=["lab"])


@router.get("/clock", response_model=LabClockOut)
def get_clock():
    return LabClockOut(now=sim_clock.get_now())


@router.post("/clock/advance", response_model=LabClockOut)
def advance_clock(payload: LabAdvanceClockIn):
    # The literal "replay without waiting for real market/time movements"
    # requirement (Sec. 11) - fast-forwards past a 2-minute hold in seconds.
    sim_clock.advance(payload.minutes)
    return LabClockOut(now=sim_clock.get_now())


@router.post("/override")
def set_override(payload: LabOverrideIn):
    sim_controller.set_override(payload.request_id, payload.component, payload.price)
    return {"ok": True}


@router.post("/fail-component")
def fail_component(payload: LabFailComponentIn):
    # Forces the NEXT booking attempt on this request to fail on this
    # component - consumed (one-shot) by that attempt, see sim_controller.py.
    sim_controller.set_booking_failure(payload.request_id, payload.component)
    return {"ok": True}


@router.post("/trigger-cycle", response_model=LabTriggerCycleOut)
def trigger_cycle():
    # Runs the real monitoring cycle immediately instead of waiting up to 5
    # real minutes for the scheduler - the same function the scheduler calls,
    # not a separate demo-only code path.
    return LabTriggerCycleOut(checked_request_ids=run_one_cycle())


@router.post("/reset")
def reset_lab():
    sim_controller.reset()
    sim_clock.reset()
    return {"ok": True}
