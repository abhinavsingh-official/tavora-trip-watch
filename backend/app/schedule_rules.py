"""
Enforces our check-in/check-out/transfer-buffer assumptions against actual
flight times - previously only flight dates were checked, not time of day.

Assumptions (also in docs/METHODOLOGY_REPORT.md):
  - Hotel check-in 14:00 local, check-out 11:00 local.
  - 45-minute transfer buffer each way, matching the 30km airport-hotel
    distance cabs.py already assumes for its fare model.
  - Outbound: reject arrivals after 23:00 (no guarantee of a safe transfer
    or front desk at that hour, and you'd lose the first night anyway).
  - Return: reject departures before 11:45 (checkout + buffer).
  - Crossing midnight isn't rejected on its own - an early next-day arrival
    is still well before the 14:00 check-in cutoff.
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
    """Applied per leg - a flight that violates this is excluded outright,
    not just deprioritized.
    """
    if is_outbound:
        arrival = _parse_time(arrival_time)
        return arrival <= LATEST_ACCEPTABLE_OUTBOUND_ARRIVAL

    departure = _parse_time(departure_time)
    earliest_acceptable_departure = _add_minutes(STANDARD_CHECK_OUT_TIME, TRANSFER_BUFFER_MINUTES)
    return departure >= earliest_acceptable_departure
