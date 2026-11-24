"""Brings the schema up to date (via real Alembic migrations, V7 onward -
see backend/alembic/), then inserts the three mock users and all three of
their exact requests from the assignment's Sec. 02 table. V3 adds B and C -
B's 4-adult/2-room case is the one that actually exercises occupancy math,
untested until now.
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
    # Real schema migrations, not Base.metadata.create_all - the same
    # mechanism a fresh deploy's pre-deploy step runs (see
    # backend/README.md), so seeding always exercises the real path, not a
    # parallel one that could quietly drift from it. Alembic's own Python
    # API, not a subprocess call out to the `alembic` binary, so this works
    # regardless of whether the venv's bin/ happens to be on PATH.
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
        db.add_all([user_a, user_b, user_c])
        db.commit()
        db.refresh(user_a)
        db.refresh(user_b)
        db.refresh(user_c)

        # Dates must be at least 30 days after the real submission deadline
        # (2026-11-25) per Sec. 02 - docs/internal/decision-log.md picked 2026-12-25 as
        # the safe boundary. All three requests use outbound dates past it.
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
        ]
        db.add_all(requests)
        db.commit()

        print(
            f"Seeded users {user_a.id}, {user_b.id}, {user_c.id} and requests "
            f"{[r.id for r in requests]}."
        )
    finally:
        db.close()


if __name__ == "__main__":
    run()
