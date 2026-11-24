"""Background monitoring cycle - runs run_check_and_alert for every active
request every 5 minutes, alongside the manual "check price now" button.
Started/stopped from main.py's lifespan rather than on import, so it
doesn't double-start under --reload and tests can skip it entirely.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.models import TripRequest, User
from app.monitoring import run_check_and_alert
from app.price_mutation import maybe_mutate_all_prices

logger = logging.getLogger(__name__)

CYCLE_MINUTES = 5

_scheduler = BackgroundScheduler()


def run_one_cycle(*, include_scenario: bool = True) -> list[int]:
    """Checks every active request once. Returns the IDs checked - also used
    by the Lab's "trigger cycle now" endpoint so a demo doesn't need to wait
    for the real 5 minutes (that manual button keeps checking the Scenario
    user too - it's a deliberate one-off click, not background noise).

    include_scenario=False is what the real, unattended 5-minute tick below
    uses: the Scenario user's requests were getting silently checked (and
    sometimes alerted) every 5 minutes around the clock even when nobody was
    looking at the Simulation page, flooding its own activity log and
    notifications with routine noise that had nothing to do with whatever
    scenario was actually being tested. Simulated users now only change when
    the Simulation page's own buttons are clicked.
    """
    checked_ids: list[int] = []
    db = SessionLocal()
    try:
        # nudge prices before checking, but only every few cycles - see price_mutation.py
        maybe_mutate_all_prices(db)

        query = db.query(TripRequest).filter(TripRequest.status == "active")
        if not include_scenario:
            query = query.join(User, TripRequest.user_id == User.id).filter(User.name != "Scenario")
        active_requests = query.all()
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


def _scheduled_tick() -> list[int]:
    return run_one_cycle(include_scenario=False)


def start_scheduler() -> None:
    if _scheduler.running:
        return
    _scheduler.add_job(
        _scheduled_tick,
        "interval",
        minutes=CYCLE_MINUTES,
        id="monitoring_cycle",
        replace_existing=True,
    )
    _scheduler.start()


def stop_scheduler() -> None:
    if _scheduler.running:
        _scheduler.shutdown(wait=False)
