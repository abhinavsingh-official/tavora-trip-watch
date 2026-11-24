"""Tiny in-memory TTL cache, shared by the real supplier clients.

Hotelbeds' free key only gets 50 requests/day and Sabre has its own
burst limit, so without caching every click (and every scheduler
cycle) burns a real call. A short TTL just absorbs rapid repeats
(double-clicks, a page re-fetching on mount) - it's not meant to
change how often we actually get a fresh price.

Not persisted across processes - a restart just costs one extra real
call, never a correctness problem.
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
