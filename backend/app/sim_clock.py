"""SimClock - everything that needs "now" asks this object, never the system
clock directly. V1 is real-time only (see docs/versions/V1.md Sec. 3): set_now
exists so the interface is stable for V2, when time-based expiry actually
needs to be fast-forwardable, but it's not consumed by any logic yet.
"""

from datetime import datetime


class SimClock:
    def __init__(self) -> None:
        self._override: datetime | None = None

    def get_now(self) -> datetime:
        return self._override if self._override is not None else datetime.utcnow()

    def set_now(self, when: datetime) -> None:
        self._override = when

    def reset(self) -> None:
        self._override = None


sim_clock = SimClock()
