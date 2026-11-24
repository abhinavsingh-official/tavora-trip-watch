"""
Sec. 05 explicitly asks for check-in/check-out/transfer-buffer assumptions
to be stated and enforced, not just mentioned. Before this, nothing in the
codebase looked at a flight's time of day at all - only dates were
checked (validation.py's date-order rule). This module is the real
enforcement, documented here so the assumption and the code live next to
each other.

Stated assumptions (also reflected in docs/METHODOLOGY_REPORT.md):
  - Standard hotel check-in: 14:00 local. Standard check-out: 11:00 local.
  - A minimum 45-minute transfer buffer between an airport and the hotel
    in either direction - anchored to the same assumed 30km leg distance
    app/sources/cabs.py already uses for its fare model, not a separate
    guess.
  - Outbound leg: the flight must land early enough that a same-day hotel
    check-in is still realistic - arrival after 23:00 local is rejected
    (no real guarantee of front-desk availability or a safe transfer at
    that hour, and the stay's first night would effectively be lost
    anyway).
  - Return leg: the flight must depart late enough that checkout (11:00)
    plus the transfer buffer could realistically be made - anything
    departing before 11:45 local is rejected.
  - Overnight travel (an itinerary whose arrival clock time is numerically
    earlier than its departure clock time - i.e. it crosses midnight) is
    not itself rejected; an early-morning arrival the next day is still
    well before the 14:00 check-in assumption and doesn't violate it.
"""

from datetime import time

STANDARD_CHECK_IN_TIME = time(14, 0)
STANDARD_CHECK_OUT_TIME = time(11, 0)
TRANSFER_BUFFER_MINUTES = 45

LATEST_ACCEPTABLE_OUTBOUND_ARRIVAL = time(23, 0)


def _parse_time(value: str) -> time:
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def _add_minutes(t: time, minutes: int) -> time:
    total = t.hour * 60 + t.minute + minutes
    total %= 24 * 60
    return time(total // 60, total % 60)


def satisfies_transfer_buffer(departure_time: str, arrival_time: str, is_outbound: bool) -> bool:
    """
    Applied per-leg, not per-package - a candidate flight that violates
    this is excluded from consideration entirely (Sec. 05: "reject
    combinations that violate them"), not merely deprioritized.
    """
    if is_outbound:
        arrival = _parse_time(arrival_time)
        return arrival <= LATEST_ACCEPTABLE_OUTBOUND_ARRIVAL

    departure = _parse_time(departure_time)
    earliest_acceptable_departure = _add_minutes(STANDARD_CHECK_OUT_TIME, TRANSFER_BUFFER_MINUTES)
    return departure >= earliest_acceptable_departure
