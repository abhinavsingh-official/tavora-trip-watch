"""In-memory price overrides and booking-failure injection for /api/lab/*,
read by pricing.py and routers/booking.py. Resets on restart - fine, since
these are just replay levers. The actual crash-recovery state lives in the
database (see routers/booking.py).
"""

COMPONENTS = ("flight", "hotel", "cab")
"""
"fail" - supplier rejects outright.
"unavailable" - inventory disappeared between hold and booking. Same
  compensation path as "fail" but labeled differently so you can tell a
  requote from a real supplier error.
"timeout" - supplier never responds. Component stays "unknown" and blocks
  further booking until reconciled.
"""
BOOKING_OUTCOMES = ("fail", "unavailable", "timeout")


class SimController:
    def __init__(self) -> None:
        """{(request_id, component): price}"""
        self._overrides: dict[tuple[int, str], float] = {}
        """
        {request_id: (component, outcome)} - next booking attempt for this
        request should hit this outcome on this component. Popped once, by
        the attempt that starts the process - a resume doesn't re-read it,
        since the outcome was already decided.
        """
        self._booking_failures: dict[int, tuple[str, str]] = {}
        """
        {request_id: component} - the next compensating cancellation for
        this component should itself fail, leaving it confirmed-but-needs-
        manual-intervention instead of falsely marked cancelled.
        """
        self._cancel_failures: dict[int, str] = {}
        """
        {request_id: component} - stop right after this component commits,
        as if the process crashed there. One-shot like the others.
        """
        self._restart_after: dict[int, str] = {}

    def set_override(self, request_id: int, component: str, price: float) -> None:
        if component not in COMPONENTS:
            raise ValueError(f"Unknown component '{component}', expected one of {COMPONENTS}")
        self._overrides[(request_id, component)] = price

    def pop_override(self, request_id: int, component: str) -> float | None:
        """
        One-shot, same as every other lever here - matches what the UI
        advertises ("for the next check only"). A plain get() would leave
        it silently forcing every future check too, which is surprising
        once you've moved on to testing something else.
        """
        return self._overrides.pop((request_id, component), None)

    def set_booking_failure(self, request_id: int, component: str, outcome: str = "fail") -> None:
        if component not in COMPONENTS:
            raise ValueError(f"Unknown component '{component}', expected one of {COMPONENTS}")
        if outcome not in BOOKING_OUTCOMES:
            raise ValueError(f"Unknown outcome '{outcome}', expected one of {BOOKING_OUTCOMES}")
        self._booking_failures[request_id] = (component, outcome)

    def pop_booking_failure(self, request_id: int) -> tuple[str, str] | None:
        return self._booking_failures.pop(request_id, None)

    def set_cancel_failure(self, request_id: int, component: str) -> None:
        if component not in COMPONENTS:
            raise ValueError(f"Unknown component '{component}', expected one of {COMPONENTS}")
        self._cancel_failures[request_id] = component

    def pop_cancel_failure(self, request_id: int) -> str | None:
        return self._cancel_failures.pop(request_id, None)

    def set_restart_after(self, request_id: int, component: str) -> None:
        if component not in COMPONENTS:
            raise ValueError(f"Unknown component '{component}', expected one of {COMPONENTS}")
        self._restart_after[request_id] = component

    def pop_restart_after(self, request_id: int) -> str | None:
        return self._restart_after.pop(request_id, None)

    def reset(self) -> None:
        self._overrides.clear()
        self._booking_failures.clear()
        self._cancel_failures.clear()
        self._restart_after.clear()


sim_controller = SimController()
