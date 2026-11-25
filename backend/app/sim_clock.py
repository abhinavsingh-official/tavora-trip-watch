"""Everything needing "now" asks this, never the system clock. Tracks an *offset* from real time (not a
frozen value) so time keeps ticking after a fast-forward instead of freezing "now" forever."""

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
