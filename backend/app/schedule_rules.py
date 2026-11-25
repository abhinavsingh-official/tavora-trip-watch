"""Enforces check-in/check-out/transfer-buffer assumptions against flight times, not just dates
(see docs/METHODOLOGY_REPORT.md for the full assumptions)."""

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
    """Applied per leg; a violating flight is excluded outright, not just deprioritized."""
    if is_outbound:
        arrival = _parse_time(arrival_time)
        return arrival <= LATEST_ACCEPTABLE_OUTBOUND_ARRIVAL

    departure = _parse_time(departure_time)
    earliest_acceptable_departure = _add_minutes(STANDARD_CHECK_OUT_TIME, TRANSFER_BUFFER_MINUTES)
    return departure >= earliest_acceptable_departure
