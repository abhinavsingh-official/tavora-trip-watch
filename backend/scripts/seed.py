"""Creates tables if missing, then inserts the three mock users (so the
mock-user switcher has something real to show) and User A's exact request
from the assignment's Sec. 02 table - the only request V1 actually needs.
Users B and C get their own requests in V3 (docs/SIMPLE_PLAN.md).
"""

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, SessionLocal, engine
from app.models import TripRequest, User


def run():
    Base.metadata.create_all(bind=engine)
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

        # Dates must be at least 30 days after the real submission deadline
        # (2026-11-25) per Sec. 02 - docs/DECISIONS.md picked 2026-12-25 as
        # the safe boundary.
        request_a = TripRequest(
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
        )
        db.add(request_a)
        db.commit()

        print(f"Seeded users {user_a.id}, {user_b.id}, {user_c.id} and request {request_a.id}.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
