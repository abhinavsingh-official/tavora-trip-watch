"""Thread-safe min-interval throttle for outbound supplier calls; without it a burst gets 429'd and
shows up indistinguishable from "no hotels found" in sources/hotels.py."""

import threading
import time

_locks: dict[str, threading.Lock] = {}
_last_call: dict[str, float] = {}


def throttle(key: str, min_interval_seconds: float) -> None:
    lock = _locks.setdefault(key, threading.Lock())
    with lock:
        last = _last_call.get(key, 0.0)
        wait = min_interval_seconds - (time.monotonic() - last)
        if wait > 0:
            time.sleep(wait)
        _last_call[key] = time.monotonic()
