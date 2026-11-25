"""Background monitoring cycle; started/stopped from main.py's lifespan so it doesn't double-start
under --reload and tests can skip it entirely."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.database import SessionLocal
from app.models import TripRequest, User
from app.monitoring import run_check_and_alert
from app.price_mutation import mutate_all_prices

logger = logging.getLogger(__name__)

CYCLE_MINUTES = 5

_scheduler = BackgroundScheduler()


def run_one_cycle(*, include_scenario: bool = True) -> list[int]:
    # Also used by Lab's "trigger cycle now"; include_scenario=False keeps the real tick from alerting Scenario
    checked_ids: list[int] = []
    db = SessionLocal()
    try:
        # nudge prices before checking, every tick - each market group decides for itself whether
        # it moves or sits still this cycle (see price_mutation.py's STAGNATION_PROBABILITY)
        mutate_all_prices(db)

        query = db.query(TripRequest).filter(TripRequest.status == "active")
        if not include_scenario:
            query = query.join(User, TripRequest.user_id == User.id).filter(User.name != "Scenario")
        active_requests = query.all()
        for trip_request in active_requests:
            try:
                run_check_and_alert(trip_request, db)
                checked_ids.append(trip_request.id)
            except Exception:
                # one request failing shouldn't stop the cycle; rollback required since all requests share one session
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
