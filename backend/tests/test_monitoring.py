"""The real alert state machine (Sec. 07) - first crossing, re-alert only on
a further 5% drop, silent reset above budget. Mirrors the exact sequence
manually verified against a real running server during V2's build, now
automated and repeatable (Sec. 12/15).
"""

from unittest.mock import patch

from app.models import Notification, TripRequest, User
from app.monitoring import run_check_and_alert
from app.pricing import PackageResult


def _make_request(db, budget_inr=35000):
    user = User(name="Monitoring Test User")
    db.add(user)
    db.commit()
    db.refresh(user)

    trip_request = TripRequest(
        user_id=user.id,
        origin="Mumbai",
        destination="Goa",
        outbound_date="2026-12-26",
        return_date="2026-12-29",
        adults=2,
        rooms=1,
        budget_inr=budget_inr,
    )
    db.add(trip_request)
    db.commit()
    db.refresh(trip_request)
    return trip_request


def _package(total_price, status="complete"):
    return PackageResult(
        flight_outbound_price=total_price / 2 if total_price else None,
        flight_return_price=total_price / 2 if total_price else None,
        flight_status=status,
        hotel_total_price=0.0,
        hotel_status=status,
        cab_outbound_price=0.0,
        cab_return_price=0.0,
        cab_status=status,
        taxes_fees=0.0,
        total_price=total_price,
        status=status,
        raw_sources={},
    )


def _notification_count(db, request_id):
    return db.query(Notification).filter(Notification.request_id == request_id).count()


def test_first_crossing_alerts_once(db):
    trip_request = _make_request(db, budget_inr=35000)
    with patch("app.monitoring.build_package", return_value=_package(34000)):
        run_check_and_alert(trip_request, db)
    assert _notification_count(db, trip_request.id) == 1
    db.refresh(trip_request)
    assert float(trip_request.last_alerted_total) == 34000


def test_same_price_again_does_not_realert(db):
    trip_request = _make_request(db, budget_inr=35000)
    with patch("app.monitoring.build_package", return_value=_package(34000)):
        run_check_and_alert(trip_request, db)
        run_check_and_alert(trip_request, db)
    assert _notification_count(db, trip_request.id) == 1


def test_small_drop_under_five_percent_does_not_realert(db):
    trip_request = _make_request(db, budget_inr=35000)
    with patch("app.monitoring.build_package", return_value=_package(34000)):
        run_check_and_alert(trip_request, db)
    # 34000 * 0.96 = 32640 - a real drop, but less than the 5% threshold.
    with patch("app.monitoring.build_package", return_value=_package(32640)):
        run_check_and_alert(trip_request, db)
    assert _notification_count(db, trip_request.id) == 1


def test_drop_of_at_least_five_percent_realerts(db):
    trip_request = _make_request(db, budget_inr=35000)
    with patch("app.monitoring.build_package", return_value=_package(34000)):
        run_check_and_alert(trip_request, db)
    # 34000 * 0.95 = 32300 exactly - the boundary itself should count.
    with patch("app.monitoring.build_package", return_value=_package(32300)):
        run_check_and_alert(trip_request, db)
    assert _notification_count(db, trip_request.id) == 2
    db.refresh(trip_request)
    assert float(trip_request.last_alerted_total) == 32300


def test_going_back_over_budget_silently_resets_without_a_notification(db):
    trip_request = _make_request(db, budget_inr=35000)
    with patch("app.monitoring.build_package", return_value=_package(34000)):
        run_check_and_alert(trip_request, db)
    with patch("app.monitoring.build_package", return_value=_package(50000)):
        run_check_and_alert(trip_request, db)
    assert _notification_count(db, trip_request.id) == 1  # no new notification
    db.refresh(trip_request)
    assert trip_request.last_alerted_total is None  # but the memory is cleared


def test_recrossing_after_a_reset_counts_as_a_first_crossing_not_a_realert(db):
    trip_request = _make_request(db, budget_inr=35000)
    with patch("app.monitoring.build_package", return_value=_package(34000)):
        run_check_and_alert(trip_request, db)
    with patch("app.monitoring.build_package", return_value=_package(50000)):
        run_check_and_alert(trip_request, db)  # reset
    # Only a trivial drop vs. the ORIGINAL 34000, but since it reset, this
    # should alert regardless of the 5% rule - it's a fresh first crossing.
    with patch("app.monitoring.build_package", return_value=_package(34500)):
        run_check_and_alert(trip_request, db)
    assert _notification_count(db, trip_request.id) == 2


def test_a_failed_check_does_nothing_either_way(db):
    trip_request = _make_request(db, budget_inr=35000)
    with patch("app.monitoring.build_package", return_value=_package(34000)):
        run_check_and_alert(trip_request, db)
    with patch("app.monitoring.build_package", return_value=_package(None, status="unavailable")):
        run_check_and_alert(trip_request, db)
    # No new notification, AND last_alerted_total must be untouched - a
    # failed check isn't allowed to look like a reset either.
    assert _notification_count(db, trip_request.id) == 1
    db.refresh(trip_request)
    assert float(trip_request.last_alerted_total) == 34000
