"""A minimal thread-safe min-interval throttle for outbound supplier calls.

Hotelbeds' own credentials page states an explicit burst limit (8 requests
per 4 seconds) - nothing in the original client code respected it, which
means a burst of concurrent checks (exactly what Sec. 12's 100-request load
test would produce) could get 429/403-throttled by the real supplier. That
throttling response would then hit the generic `except Exception` in
sources/hotels.py and get reported as "unavailable" - indistinguishable from
"no hotels exist," which is a real correctness problem, not just noise: it
silently misrepresents our own rate-limiting as the supplier having nothing.

This enforces a minimum spacing between calls instead - simple, blocking (safe
here because FastAPI's sync `def` routes already run in a thread pool), and
good enough for a solo-prototype's real call volume.
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
