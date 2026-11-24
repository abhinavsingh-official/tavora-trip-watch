"""
Real bug found live: advance() used to store a frozen absolute timestamp,
so "now" stopped moving at all after a single clock fast-forward - every
timestamp anywhere in the app (not just the Scenario user's) came back
identical until Reset was clicked. Two notifications created minutes apart
in production had byte-identical reviewed_at/held_until values because of
this. Fixed by tracking an offset from real time instead of a frozen value.
"""

import time

from app.sim_clock import SimClock


def test_advance_shifts_time_forward_but_does_not_freeze_it():
    clock = SimClock()
    before = clock.get_now()
    clock.advance(5)
    after_advance = clock.get_now()
    assert (after_advance - before).total_seconds() >= 5 * 60

    time.sleep(0.05)
    later = clock.get_now()
    # real time must still be moving, even after a fast-forward - this is
    # exactly what broke: later used to equal after_advance exactly
    assert later > after_advance


def test_reset_returns_to_real_time():
    clock = SimClock()
    clock.advance(10)
    clock.reset()
    assert clock._offset.total_seconds() == 0
