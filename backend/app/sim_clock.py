"""SimClock - everything that needs "now" asks this, never the system
clock directly. A hold's 2-minute expiry is checked against
sim_clock.get_now(), and advance() lets a demo fast-forward past it in
seconds instead of waiting around.

Tracks an *offset* from real time, not a frozen absolute value - an
earlier version stored advance()'s result as a fixed override, which froze
"now" at that exact instant forever (every timestamp anywhere in the app -
not just the Scenario user's - came back identical until Reset was
clicked, since get_now() never advanced on its own again). This way real
time keeps ticking normally after a fast-forward, just shifted ahead by
however much was advanced.

Always timezone-aware, matching the DateTime(timezone=True) columns in
models.py - a naive timestamp gets misread as local time by the
browser.
"""

from datetime import datetime, timedelta, timezone


class SimClock:
    def __init__(self) -> None:
        self._offset = timedelta(0)

    def get_now(self) -> datetime:
        return datetime.now(timezone.utc) + self._offset

    def set_now(self, when: datetime) -> None:
        self._offset = when - datetime.now(timezone.utc)

    def advance(self, minutes: float) -> datetime:
        self._offset += timedelta(minutes=minutes)
        return self.get_now()

    def reset(self) -> None:
        self._offset = timedelta(0)


sim_clock = SimClock()
