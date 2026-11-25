"""Everything needing "now" asks this, never the system clock. Tracks an *offset* from real time (not a
frozen value) so time keeps ticking after a fast-forward instead of freezing "now" forever.

The offset only ever applies to the Simulation sandbox: `get_now()` takes an explicit `simulated` flag
so a caller has to say which clock it means, rather than one shared clock silently fast-forwarding the
real demo users (A/B/C) along with it whenever someone drags the Simulation page's Clock lever."""

from datetime import datetime, timedelta, timezone


class SimClock:
    def __init__(self) -> None:
        self._offset = timedelta(0)

    def get_now(self, *, simulated: bool) -> datetime:
        real_now = datetime.now(timezone.utc)
        return real_now + self._offset if simulated else real_now

    def set_now(self, when: datetime) -> None:
        self._offset = when - datetime.now(timezone.utc)

    def advance(self, minutes: float) -> datetime:
        self._offset += timedelta(minutes=minutes)
        return self.get_now(simulated=True)

    def reset(self) -> None:
        self._offset = timedelta(0)


sim_clock = SimClock()


def now_for_request(trip_request) -> datetime:
    """`get_now()`, but figures out `simulated` from the trip's own owner instead of making every
    caller remember to check: only the Simulation sandbox's "Scenario" user (see User.is_simulated)
    is fast-forwarded, real demo users (A/B/C) always see real wall-clock time."""
    return sim_clock.get_now(simulated=bool(trip_request.user and trip_request.user.is_simulated))
