"""Runs Alembic migrations up to head, then inserts the three mock users and
their trip requests from the assignment brief, plus one "Scenario" user
the Simulation page runs its demos against. User B's 4-adult/2-room case
is the one that actually exercises occupancy math.
"""

import sys
from datetime import date
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from alembic import command
from alembic.config import Config

from app.database import SessionLocal
from app.models import TripRequest, User


def run():
    """Use real migrations here, not Base.metadata.create_all, so seeding
    exercises the same path a deploy does. Alembic's Python API rather than
    shelling out to the CLI binary, so it works even if venv/bin isn't on PATH.
    """
    alembic_cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    command.upgrade(alembic_cfg, "head")

    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            print("Already seeded - skipping. Run reset.py first to start clean.")
            return

        user_a = User(name="User A")
        user_b = User(name="User B")
        user_c = User(name="User C")
        """
        A fourth, clearly-labeled identity the Simulation page always runs
        its demos against, instead of borrowing whichever real demo user
        happens to be selected in the sidebar - keeps scenario runs
        visibly separate from the three reviewer-facing personas above.
        """
        scenario_user = User(name="Scenario")
        db.add_all([user_a, user_b, user_c, scenario_user])
        db.commit()
        db.refresh(user_a)
        db.refresh(user_b)
        db.refresh(user_c)
        db.refresh(scenario_user)

        # Outbound dates need to be comfortably past the submission deadline,
        # so we use late December here.
        requests = [
            TripRequest(
                user_id=user_a.id,
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
                user_id=user_b.id,
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
            TripRequest(
                user_id=user_c.id,
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
            ),
            # Scenario user's two requests reuse User A's and User B's exact
            # search keys (same dates/occupancy), so they already have real
            # cached hotel/flight data behind them with no extra fetch -
            # and give the shared-room-contention demo two ready IDs to race.
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

        print(
            f"Seeded users {user_a.id}, {user_b.id}, {user_c.id}, {scenario_user.id} (Scenario) "
            f"and requests {[r.id for r in requests]}."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
