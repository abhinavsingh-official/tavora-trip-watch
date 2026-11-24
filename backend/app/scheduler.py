"""Background monitoring cycle - runs run_check_and_alert for every active
request every 5 minutes, alongside the manual "check price now" button.
Started/stopped from main.py's lifespan rather than on import, so it
doesn't double-start under --reload and tests can skip it entirely.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.models import TripRequest
from app.monitoring import run_check_and_alert
from app.price_mutation import maybe_mutate_all_prices

logger = logging.getLogger(__name__)

CYCLE_MINUTES = 5

_scheduler = BackgroundScheduler()


def run_one_cycle() -> list[int]:
    """Checks every active request once. Returns the IDs checked - also used
    by the Lab's "trigger cycle now" endpoint so a demo doesn't need to wait
    for the real 5 minutes.
    """
    checked_ids: list[int] = []
    db = SessionLocal()
    try:
        # nudge prices before checking, but only every few cycles - see price_mutation.py
        maybe_mutate_all_prices(db)

        active_requests = db.query(TripRequest).filter(TripRequest.status == "active").all()
        for trip_request in active_requests:
            try:
                run_check_and_alert(trip_request, db)
                checked_ids.append(trip_request.id)
            except Exception:
                """One request failing shouldn't stop the rest of the cycle.
                db.rollback() is required here - all requests share one
                session, and Postgres won't let you do anything else on it
                after an error until it's rolled back.
                """
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
