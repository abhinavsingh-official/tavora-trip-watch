"""The automatic monitoring cycle (Sec. 06) - runs app.monitoring.run_check_and_alert
for every active request every 5 minutes, alongside (not instead of) the
manual "check price now" button. Started/stopped from main.py's FastAPI
lifespan, not imported as a side effect, so it doesn't start twice under
`--reload` and can be left out entirely in a future test environment.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.models import TripRequest
from app.monitoring import run_check_and_alert

logger = logging.getLogger(__name__)

CYCLE_MINUTES = 5

_scheduler = BackgroundScheduler()


def run_one_cycle() -> list[int]:
    """Checks every active request once. Returns the IDs actually checked -
    also used by the Lab's "trigger cycle now" endpoint, so a demo doesn't
    have to wait for the real 5 minutes to see this run."""
    checked_ids: list[int] = []
    db = SessionLocal()
    try:
        active_requests = db.query(TripRequest).filter(TripRequest.status == "active").all()
        for trip_request in active_requests:
            try:
                run_check_and_alert(trip_request, db)
                checked_ids.append(trip_request.id)
            except Exception:
                # One request's real supplier call failing must not stop the
                # rest of the cycle from running - each is independent.
                # db.rollback() matters here specifically: all requests in
                # this cycle share one session, and Postgres aborts a
                # transaction on error until it's rolled back - without this,
                # one failure would silently poison every request checked
                # after it in the same cycle, not just this one.
                logger.exception("Monitoring cycle failed for request %s", trip_request.id)
                db.rollback()
    finally:
        db.close()
    return checked_ids


def start_scheduler() -> None:
    if _scheduler.running:
        return
    _scheduler.add_job(
        run_one_cycle,
        "interval",
        minutes=CYCLE_MINUTES,
        id="monitoring_cycle",
        replace_existing=True,
    )
    _scheduler.start()


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
