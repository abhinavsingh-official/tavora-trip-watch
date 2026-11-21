"""A tiny in-memory TTL cache, shared by the real supplier clients.

Why this exists: Hotelbeds' free key is capped at 50 requests/day (confirmed
by exhausting it during testing, docs/NOTES.md round 10) and Sabre has its own
documented burst limit. Without this, every single "check price now" click -
and, once V2's 5-minute scheduler exists, every scheduled cycle for every
active request - makes a brand-new real call, which burns through a scarce
daily quota far faster than the actual number of *meaningfully different*
price checks a user would ever want. A short TTL (a few minutes, well under
V2's planned 5-minute cycle) absorbs rapid repeats (a double-click, opening
the same offer twice, a page that re-fetches on mount) without changing the
actual "how often do we get a fresh real price" cadence that V2 will decide.

Deliberately NOT persisted/shared across processes, same as sim_clock/
sim_controller - a process restart just means the next call is a real one,
which is always safe, just slightly wasteful of one quota unit.
"""

import time
from typing import Any

_store: dict[str, tuple[float, Any]] = {}


def get(key: str, ttl_seconds: float) -> Any | None:
    entry = _store.get(key)
    if entry is None:
        return None
    stored_at, value = entry
    if time.time() - stored_at > ttl_seconds:
        return None
    return value


def set(key: str, value: Any) -> None:
    _store[key] = (time.time(), value)


def clear() -> None:
    _store.clear()
