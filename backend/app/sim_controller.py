"""SimController - in-memory price overrides and booking-failure injection,
set via /api/lab/* and read by pricing.py / routers/booking.py. Clears on
process restart, which is fine - these are demo/replay levers, not state
that needs to survive a crash (the booking workflow's own crash-recovery
behavior is what's being demonstrated with them, and that lives in the
database, not here - see routers/booking.py).
"""

COMPONENTS = ("flight", "hotel", "cab")
"""
"fail" - V2's original scenario: supplier rejects outright.
"unavailable" - inventory disappeared between hold and booking (Sec. 09
  row 2) - same compensation shape as "fail", distinct label so the
  difference ("requote, not a supplier error") is visible in the result.
"timeout" - the supplier's response never resolves (Sec. 09 row 4) - leaves
  the component "unknown" and blocks further booking until reconciled.
"""
BOOKING_OUTCOMES = ("fail", "unavailable", "timeout")


class SimController:
    def __init__(self) -> None:
        """{(request_id, component): price}"""
        self._overrides: dict[tuple[int, str], float] = {}
        """
        {request_id: (component, outcome)} - "the next booking attempt for
        this request should hit this outcome on this component." Consumed
        (popped) once, by the booking attempt that starts the process -
        never re-read by a resume (see routers/booking.py), since a resume
        continues an outcome already decided, not a fresh one.
        """
        self._booking_failures: dict[int, tuple[str, str]] = {}
        """
        {request_id: component} - the next compensating cancellation for
        this component should itself fail (Sec. 09 row 6 - "cancellation
        fails"), leaving it visibly confirmed-but-needing-manual-
        intervention rather than falsely marked cancelled.
        """
        self._cancel_failures: dict[int, str] = {}
        """
        {request_id: component} - stop processing right after this
        component commits, as if the process crashed there (Sec. 09 row 5
        / Sec. 11 scenario 6). One-shot, same as the others.
        """
        self._restart_after: dict[int, str] = {}

    def set_override(self, request_id: int, component: str, price: float) -> None:
        if component not in COMPONENTS:
            raise ValueError(f"Unknown component '{component}', expected one of {COMPONENTS}")
        self._overrides[(request_id, component)] = price

    def get_override(self, request_id: int, component: str) -> float | None:
        return self._overrides.get((request_id, component))

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
