"""Thread-safe min-interval throttle for outbound supplier calls.

Hotelbeds caps us at 8 requests per 4 seconds. Without this, a burst of
concurrent checks gets 429/403'd, and that error falls into the generic
`except Exception` in sources/hotels.py and comes back as "unavailable" -
indistinguishable from the supplier genuinely having no hotels.

Blocking is fine here since FastAPI's sync routes already run in a
thread pool, and it's plenty for this scale of traffic.
"""

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
