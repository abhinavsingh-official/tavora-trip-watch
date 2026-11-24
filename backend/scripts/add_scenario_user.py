"""
One-time patch for a database that was already seeded before the
"Scenario" user existed (scripts/seed.py now creates it on a fresh seed,
but production was seeded long before this). Idempotent - skips if a user
named "Scenario" already exists.

Run once: .venv/bin/python scripts/add_scenario_user.py
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
        existing = db.query(User).filter(User.name == "Scenario").first()
        if existing is not None:
            print(f"Already present as user {existing.id} - skipping.")
            return

        scenario_user = User(name="Scenario")
        db.add(scenario_user)
        db.commit()
        db.refresh(scenario_user)

        # Same two search keys as User A's and User B's requests, so both
        # already have real cached hotel/flight data behind them.
        requests = [
            TripRequest(
                user_id=scenario_user.id,
                origin="Mumbai",
                destination="Goa",
                outbound_date=date(2026, 12, 26),
                return_date=date(2026, 12, 29),
                adults=2,
                rooms=1,
                budget_inr=35000,
                max_stops_outbound=2,
                max_stops_return=2,
                min_star_rating=0,
                checked_baggage=False,
            ),
            TripRequest(
                user_id=scenario_user.id,
                origin="Delhi",
                destination="Goa",
                outbound_date=date(2026, 12, 26),
                return_date=date(2026, 12, 29),
                adults=4,
                rooms=2,
                budget_inr=65000,
                max_stops_outbound=2,
                max_stops_return=2,
                min_star_rating=0,
                checked_baggage=False,
            ),
        ]
        db.add_all(requests)
        db.commit()
        print(f"Added Scenario user {scenario_user.id} with requests {[r.id for r in requests]}.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
