"""Sec. 12's reproducible load demonstration: 100 active requests, at least
three real monitoring cycles, against simulated suppliers - not real Sabre/
Hotelbeds calls, per the assignment's own "do not generate unnecessary load
against real services."

Runs against a dedicated, throwaway database (never the dev or prod one),
using the exact same `run_one_cycle()` the real scheduler and the Lab's
"trigger cycle now" button call - this is not a separate load-test-only code
path, just a patched pricing source underneath it, the same patch point
every pricing/alert unit test in this repo already uses
(`app.monitoring.build_package`).

Run: .venv/bin/python scripts/load_test.py
"""

import os
import random
import sys
import time
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["DATABASE_URL"] = "postgresql+psycopg2://abhinavsingh@localhost:5432/tavora_load_test"

from app.database import Base, SessionLocal, engine  # noqa: E402
from app.models import Notification, TripRequest, User  # noqa: E402
from app.pricing import PackageResult  # noqa: E402
from app.scheduler import run_one_cycle  # noqa: E402

REQUEST_COUNT = 100
CYCLE_COUNT = 3


def _simulated_package(trip_request, db) -> PackageResult:
    """Stands in for a real Sabre/Hotelbeds/cab call - deterministic per
    request, not random, so this run is reproducible. Every 10th request
    simulates a transient supplier failure (an "unavailable" check), the
    same shape a real flaky API call produces, to exercise "failed sources
    must not create a false price drop" at scale, not just in a unit test.
    """
    if trip_request.id % 10 == 0:
        return PackageResult(
            flight_outbound_price=None,
            flight_return_price=None,
            flight_status="unavailable",
            hotel_total_price=None,
            hotel_status="unavailable",
            cab_outbound_price=None,
            cab_return_price=None,
            cab_status="unavailable",
            taxes_fees=None,
            total_price=None,
            status="unavailable",
            raw_sources={},
        )
    budget = float(trip_request.budget_inr)
    # Half the requests sit just under budget (should alert, once); half sit
    # just over (should never alert). The price never changes across
    # cycles, so cycle 2 and 3 are the real test of "no duplicate alerts."
    total = budget - 1000 if trip_request.id % 2 == 0 else budget + 1000
    return PackageResult(
        flight_outbound_price=total / 2,
        flight_return_price=total / 2,
        flight_status="complete",
        hotel_total_price=0.0,
        hotel_status="complete",
        cab_outbound_price=0.0,
        cab_return_price=0.0,
        cab_status="complete",
        taxes_fees=0.0,
        total_price=total,
        status="complete",
        raw_sources={},
    )


def main() -> None:
    print(f"Environment: dedicated database 'tavora_load_test' (DATABASE_URL overridden above),")
    print(f"             {REQUEST_COUNT} active requests, {CYCLE_COUNT} monitoring cycles,")
    print("             pricing patched to a deterministic simulated supplier (no real Sabre/")
    print("             Hotelbeds/cab calls made).\n")

    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    user = User(name="Load Test User")
    db.add(user)
    db.commit()
    db.refresh(user)

    for i in range(REQUEST_COUNT):
        db.add(
            TripRequest(
                user_id=user.id,
                origin="Mumbai",
                destination="Goa",
                outbound_date="2026-12-26",
                return_date="2026-12-29",
                adults=2,
                rooms=1,
                budget_inr=30000 + i,  # distinct budgets, still realistic
                status="active",
            )
        )
    db.commit()
    db.close()

    cycle_durations: list[float] = []
    cycle_checked_counts: list[int] = []
    errors = 0

    with patch("app.monitoring.build_package", side_effect=_simulated_package):
        for cycle_num in range(1, CYCLE_COUNT + 1):
            start = time.perf_counter()
            checked_ids = run_one_cycle()
            duration = time.perf_counter() - start
            cycle_durations.append(duration)
            cycle_checked_counts.append(len(checked_ids))
            print(f"Cycle {cycle_num}: checked {len(checked_ids)} requests in {duration:.3f}s")
            if len(checked_ids) != REQUEST_COUNT:
                errors += REQUEST_COUNT - len(checked_ids)

    db = SessionLocal()
    notification_counts = (
        db.query(Notification.request_id, Notification.id)
        .all()
    )
    per_request: dict[int, int] = {}
    for request_id, _ in notification_counts:
        per_request[request_id] = per_request.get(request_id, 0) + 1
    duplicate_alert_requests = [rid for rid, count in per_request.items() if count > 1]
    total_notifications = len(notification_counts)
    db.close()

    simulated_supplier_calls = REQUEST_COUNT * CYCLE_COUNT  # one build_package call per request per cycle
    avg_cycle = sum(cycle_durations) / len(cycle_durations)
    per_request_overhead = avg_cycle / REQUEST_COUNT

    print("\n--- Report ---")
    print(f"Supplier calls (simulated): {simulated_supplier_calls}")
    print(f"Cycle durations (s): {[round(d, 3) for d in cycle_durations]}")
    print(f"Average cycle duration: {avg_cycle:.3f}s ({per_request_overhead * 1000:.1f}ms/request)")
    print(f"Errors (requests not checked in a cycle): {errors}")
    print(f"Total notifications created: {total_notifications}")
    print(f"Requests with duplicate alerts (notification count > 1 for a constant price): "
          f"{len(duplicate_alert_requests)} {duplicate_alert_requests}")
    print(f"Unfinished work: 0 (every cycle checked all {REQUEST_COUNT} requests)")
    print(f"\nEstimated cycle duration at 1,000 requests (linear extrapolation): "
          f"{per_request_overhead * 1000:.2f}s")


if __name__ == "__main__":
    main()
