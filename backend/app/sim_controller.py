"""SimController - in-memory price overrides and (V2) booking-failure
injection, set via /api/lab/* and read by pricing.py / routers/booking.py.
Clears on process restart, which is fine for V1/V2 - these are demo/replay
levers, not state that needs to survive a crash.
"""

COMPONENTS = ("flight", "hotel", "cab")


class SimController:
    def __init__(self) -> None:
        # {(request_id, component): price}
        self._overrides: dict[tuple[int, str], float] = {}
        # {request_id: component} - "the next booking attempt for this
        # request should fail on this component." Consumed (popped) by the
        # first booking attempt that reads it, so it only fires once per
        # set call, not forever.
        self._booking_failures: dict[int, str] = {}

    def set_override(self, request_id: int, component: str, price: float) -> None:
        if component not in COMPONENTS:
            raise ValueError(f"Unknown component '{component}', expected one of {COMPONENTS}")
        self._overrides[(request_id, component)] = price

    def get_override(self, request_id: int, component: str) -> float | None:
        return self._overrides.get((request_id, component))

    def set_booking_failure(self, request_id: int, component: str) -> None:
        if component not in COMPONENTS:
            raise ValueError(f"Unknown component '{component}', expected one of {COMPONENTS}")
        self._booking_failures[request_id] = component

    def pop_booking_failure(self, request_id: int) -> str | None:
        return self._booking_failures.pop(request_id, None)

    def reset(self) -> None:
        self._overrides.clear()
        self._booking_failures.clear()


sim_controller = SimController()
