from fastapi import APIRouter

from app.schemas import LabClockOut, LabOverrideIn
from app.sim_clock import sim_clock
from app.sim_controller import sim_controller

# Everything here is explicitly dev/demo-only - the Scenario Lab, never called
# by the real user-facing screens. See docs/DECISIONS.md "Simulation design".
router = APIRouter(prefix="/api/lab", tags=["lab"])


@router.get("/clock", response_model=LabClockOut)
def get_clock():
    return LabClockOut(now=sim_clock.get_now())


@router.post("/override")
def set_override(payload: LabOverrideIn):
    sim_controller.set_override(payload.request_id, payload.component, payload.price)
    return {"ok": True}


@router.post("/reset")
def reset_lab():
    sim_controller.reset()
    sim_clock.reset()
    return {"ok": True}
