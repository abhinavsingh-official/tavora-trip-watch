"""The real alert state machine (Sec. 07), shared by the manual "check price
now" button and the V2 scheduler - one implementation, not two copies that
can drift apart.

Rule, stated precisely:
- A failed/incomplete check does nothing either way - no alert, no reset.
- The first time a complete package is at or under budget, alert once.
- While it stays under budget, alert again only if the price has dropped at
  least 5% further below the total we last alerted at - not just "still
  under budget."
- A complete package back over budget silently clears that memory, so the
  next crossing counts as a first crossing again, not a re-alert.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import Notification, PriceObservation, TripRequest
from app.pricing import build_package
from app.sim_clock import sim_clock
from app.validation import validate_date_order

RE_ALERT_DROP_FRACTION = 0.05
HOLD_DURATION_MINUTES = 2


def create_observation(trip_request: TripRequest, db: Session) -> PriceObservation:
    """Runs a real price check and persists it. Public (no leading
    underscore) since it's deliberately shared across routers, not private
    to this module.

    Validated here, not just at request creation/edit time (app/
    routers/requests.py) - this is the one choke point both the manual
    "check price now" button and the V2 scheduler go through, so it also
    catches a request that became invalid before this validation existed,
    without spending a real supplier call pricing a trip that never
    happens."""
    validate_date_order(trip_request.outbound_date, trip_request.return_date)
    package = build_package(trip_request)

    observation = PriceObservation(
        request_id=trip_request.id,
        observed_at=sim_clock.get_now(),
        flight_outbound_price=package.flight_outbound_price,
        flight_return_price=package.flight_return_price,
        flight_status=package.flight_status,
        hotel_total_price=package.hotel_total_price,
        hotel_status=package.hotel_status,
        cab_outbound_price=package.cab_outbound_price,
        cab_return_price=package.cab_return_price,
        cab_status=package.cab_status,
        taxes_fees=package.taxes_fees,
        total_price=package.total_price,
        status=package.status,
        raw_sources=package.raw_sources,
        # Audit finding #8: the filter actually in effect *now*, captured
        # once - app/story.py reads this back instead of re-reading the
        # request's current (possibly since-edited) value.
        min_star_rating_used=trip_request.min_star_rating,
    )
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return observation


def run_check_and_alert(trip_request: TripRequest, db: Session) -> PriceObservation:
    observation = create_observation(trip_request, db)

    # Two near-simultaneous checks on the same request could otherwise both
    # read last_alerted_total before either writes it, both deciding
    # independently to alert - the same transaction-scoped advisory lock
    # from V1, now guarding the richer state machine below instead of the
    # simple "has any notification ever existed" check.
    db.execute(
        text("SELECT pg_advisory_xact_lock(:request_id)"), {"request_id": trip_request.id}
    )
    # Re-read within the lock - another transaction may have changed
    # last_alerted_total between this function starting and the lock being
    # acquired.
    db.refresh(trip_request)

    if observation.status != "complete" or observation.total_price is None:
        # A failed/incomplete check does nothing either way (Sec. 07) - not
        # even releasing or touching last_alerted_total.
        db.commit()
        return observation

    total = float(observation.total_price)
    budget = float(trip_request.budget_inr)
    last_alerted = (
        float(trip_request.last_alerted_total)
        if trip_request.last_alerted_total is not None
        else None
    )

    if total <= budget:
        first_crossing = last_alerted is None
        dropped_further = last_alerted is not None and total <= last_alerted * (
            1 - RE_ALERT_DROP_FRACTION
        )
        if first_crossing or dropped_further:
            notification = Notification(
                request_id=trip_request.id,
                observation_id=observation.id,
                created_at=sim_clock.get_now(),
            )
            db.add(notification)
            trip_request.last_alerted_total = observation.total_price
    elif last_alerted is not None:
        # Back over budget after having an active alert - silent reset, no
        # notification, so the next crossing is treated as a first crossing.
        trip_request.last_alerted_total = None

    db.commit()
    return observation
