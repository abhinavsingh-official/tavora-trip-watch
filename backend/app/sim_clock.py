"""SimClock - everything that needs "now" asks this, never the system
clock directly. A hold's 2-minute expiry is checked against
sim_clock.get_now(), and advance() lets a demo fast-forward past it in
seconds instead of waiting around.

Always timezone-aware, matching the DateTime(timezone=True) columns in
models.py - a naive timestamp gets misread as local time by the
browser.
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
        """Advances from the current effective value, not a fixed origin,
        so repeated small advances stack the way you'd expect."""
        self._override = self.get_now() + timedelta(minutes=minutes)
        return self._override

    def reset(self) -> None:
        self._override = None


sim_clock = SimClock()
