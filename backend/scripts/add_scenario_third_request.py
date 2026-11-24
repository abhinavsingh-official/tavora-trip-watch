"""
One-time patch for a database that already has the "Scenario" user with
its original two requests (add_scenario_user.py already ran there before
this third slot existed). Idempotent - skips if a Jaipur request already
exists for that user.

Run once: .venv/bin/python scripts/add_scenario_third_request.py
"""

import sys
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal
from app.models import TripRequest, User


def run():
    db = SessionLocal()
    try:
        scenario_user = db.query(User).filter(User.name == "Scenario").first()
        if scenario_user is None:
            print("No Scenario user found - run add_scenario_user.py first.")
            return

        existing = (
            db.query(TripRequest)
            .filter(TripRequest.user_id == scenario_user.id, TripRequest.destination == "Jaipur")
            .first()
        )
        if existing is not None:
            print(f"Already present as request {existing.id} - skipping.")
            return

        # Same search key as User C's request, so it already has real
        # cached hotel/flight data behind it.
        request = TripRequest(
            user_id=scenario_user.id,
            origin="Mumbai",
            destination="Jaipur",
            outbound_date=date(2026, 12, 26),
            return_date=date(2026, 12, 28),
            adults=2,
            rooms=1,
            budget_inr=30000,
            max_stops_outbound=2,
            max_stops_return=2,
            min_star_rating=0,
            checked_baggage=False,
        )
        db.add(request)
        db.commit()
        db.refresh(request)
        print(f"Added request {request.id} to Scenario user {scenario_user.id}.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
