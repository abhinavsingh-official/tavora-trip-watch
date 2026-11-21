"""SimClock - everything that needs "now" asks this object, never the system
clock directly. V2 actually consumes this: a 2-minute hold's expiry is
checked against sim_clock.get_now(), and advance() is what lets a demo fast-
forward past it in seconds instead of waiting 2 real minutes.

Always timezone-aware (datetime.now(timezone.utc), not datetime.utcnow()) -
paired with the DateTime(timezone=True) columns in models.py, this is what
makes every timestamp round-trip with an explicit UTC offset. Without it, a
browser outside UTC silently misreads a naive UTC timestamp as local time -
found by a real browser test showing a brand-new hold as already expired.
"""

from datetime import datetime, timedelta, timezone


class SimClock:
    def __init__(self) -> None:
        self._override: datetime | None = None

    def get_now(self) -> datetime:
        return self._override if self._override is not None else datetime.now(timezone.utc)

    def set_now(self, when: datetime) -> None:
        self._override = when

    def advance(self, minutes: float) -> datetime:
        """Moves the clock forward from its current effective value (real
        time, if nothing's been overridden yet) - not from some fixed
        origin, so repeated small advances compose the way you'd expect."""
        self._override = self.get_now() + timedelta(minutes=minutes)
        return self._override

    def reset(self) -> None:
        self._override = None


sim_clock = SimClock()
