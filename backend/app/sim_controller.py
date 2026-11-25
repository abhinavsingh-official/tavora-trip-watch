"""In-memory price overrides and booking-failure injection for /api/lab/*. Resets on restart; the
real crash-recovery state lives in the database (see routers/booking.py)."""

COMPONENTS = ("flight", "hotel", "cab")
# "fail"/"unavailable" are the same path, different label; "timeout" leaves it "unknown" until reconciled
BOOKING_OUTCOMES = ("fail", "unavailable", "timeout")


class SimController:
    def __init__(self) -> None:
        self._overrides: dict[tuple[int, str], float] = {}  # (request_id, component) -> price
        # request_id -> (component, outcome); popped once by the attempt that starts the process
        self._booking_failures: dict[int, tuple[str, str]] = {}
        # request_id -> component whose next compensating cancellation should itself fail
        self._cancel_failures: dict[int, str] = {}
        # request_id -> component to stop right after, as if the process crashed there
        self._restart_after: dict[int, str] = {}

    def set_override(self, request_id: int, component: str, price: float) -> None:
        if component not in COMPONENTS:
            raise ValueError(f"Unknown component '{component}', expected one of {COMPONENTS}")
        self._overrides[(request_id, component)] = price

    def pop_override(self, request_id: int, component: str) -> float | None:
        # One-shot, matching the UI's "for the next check only"; a plain get() would force every future check too
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
