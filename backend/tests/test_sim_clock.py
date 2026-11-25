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
    before = clock.get_now(simulated=True)
    clock.advance(5)
    after_advance = clock.get_now(simulated=True)
    assert (after_advance - before).total_seconds() >= 5 * 60

    time.sleep(0.05)
    later = clock.get_now(simulated=True)
    # real time must still be moving, even after a fast-forward - this is
    # exactly what broke: later used to equal after_advance exactly
    assert later > after_advance


def test_reset_returns_to_real_time():
    clock = SimClock()
    clock.advance(10)
    clock.reset()
    assert clock._offset.total_seconds() == 0


def test_advancing_the_simulated_clock_does_not_move_the_real_one():
    """The actual fix for 'fast-forwarding affects the whole app, not just the sandbox' (known issue):
    advance() only ever moves the offset get_now(simulated=True) reads - simulated=False (what real
    demo users A/B/C see) must stay at real wall-clock time regardless of how far the sandbox jumps."""
    clock = SimClock()
    before_real = clock.get_now(simulated=False)
    clock.advance(60)
    after_real = clock.get_now(simulated=False)
    assert (after_real - before_real).total_seconds() < 5  # only real elapsed time, not the 60-minute jump
    assert (clock.get_now(simulated=True) - after_real).total_seconds() >= 59 * 60
