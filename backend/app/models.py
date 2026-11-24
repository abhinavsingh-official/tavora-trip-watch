from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.database import Base


def _utcnow() -> datetime:
    """
    Timezone-aware, not datetime.utcnow() (naive). Paired with
    DateTime(timezone=True) columns below, this is what makes every
    timestamp this app emits serialize with an explicit UTC offset -
    without it, a naive UTC timestamp gets silently misread as local time
    by a browser, which is exactly what made a brand-new hold look already
    expired the instant it was created (found via a real browser test, not
    inspection - see docs/internal/decision-log.md).
    """
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


class TripRequest(Base):
    __tablename__ = "trip_requests"

    id = Column(Integer, primary_key=True)
    """
    Postgres does not auto-index foreign keys (only primary keys) -
    index=True here matters once a user has more than a handful of
    requests, since every Dashboard load filters on this column.
    """
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    origin = Column(String, nullable=False)
    destination = Column(String, nullable=False)
    outbound_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=False)
    adults = Column(Integer, nullable=False)
    rooms = Column(Integer, nullable=False)
    budget_inr = Column(Numeric(10, 2), nullable=False)
    max_stops_outbound = Column(Integer, nullable=False, default=2)
    max_stops_return = Column(Integer, nullable=False, default=2)
    min_star_rating = Column(Integer, nullable=False, default=0)
    checked_baggage = Column(Boolean, nullable=False, default=False)
    """
    "active" is the only status V1 acts on; "paused"/"cancelled" exist now so
    V3's edit/pause/cancel work needs no schema change later.
    """
    status = Column(String, nullable=False, default="active")

    """
    The real alert state machine's memory (Sec. 07): null means "no active
    alert" - either never crossed under budget, or crossed back over budget
    and silently reset. Non-null is the total we last alerted at, used to
    decide whether a further drop is "at least 5% more" (re-alert) or not
    (stay quiet). This single column is what V2 adds to make the real
    first-crossing/re-alert/reset rule possible - V1 only ever checked
    "has any notification ever existed."
    """
    last_alerted_total = Column(Numeric(10, 2), nullable=True)

    """
    V7: when this request's own fields last changed (create or edit) - not
    touched by pause/cancel/reactivate, which are status transitions, not
    trip-detail edits. Lets the Dashboard tell "this total reflects the
    trip as it is now" from "this total predates your last edit" (audit
    finding #1) - without this, nothing on screen could ever tell the two
    apart.
    """
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    user = relationship("User")


class PriceObservation(Base):
    __tablename__ = "price_observations"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("trip_requests.id"), nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    """
    A composite index matching the actual query shape (routers/check.py's
    list_observations: filter by request_id, order by observed_at desc) -
    this will matter once the V2 scheduler starts appending rows every 5
    minutes; invisible at today's row counts but worth having from day one
    rather than retrofitting once it's already slow.
    """
    __table_args__ = (Index("ix_price_observations_request_observed", "request_id", "observed_at"),)

    flight_outbound_price = Column(Numeric(10, 2), nullable=True)
    flight_return_price = Column(Numeric(10, 2), nullable=True)
    flight_status = Column(String, nullable=False, default="unavailable")

    hotel_total_price = Column(Numeric(10, 2), nullable=True)
    hotel_status = Column(String, nullable=False, default="unavailable")

    cab_outbound_price = Column(Numeric(10, 2), nullable=True)
    cab_return_price = Column(Numeric(10, 2), nullable=True)
    cab_status = Column(String, nullable=False, default="unavailable")

    taxes_fees = Column(Numeric(10, 2), nullable=True)
    total_price = Column(Numeric(10, 2), nullable=True)
    """
    Package-level status: "complete" only if every component above is
    "complete"; otherwise "provisional" (something's missing/approximate but
    present) or "unavailable" (a component couldn't be fetched at all).
    Only "complete" can ever trigger a budget alert (assignment Sec. 05).
    """
    status = Column(String, nullable=False, default="unavailable")

    """
    The full raw response from each real source call that produced this
    observation - kept for traceability and the data-source dossier's
    "sanitized sample data" / field-mapping requirement. Null for cabs
    (simulated, no external response to keep).
    """
    raw_sources = Column(JSONB, nullable=True)

    """
    V7: the min-star filter actually in effect when this check ran -
    captured once, here, rather than re-read live off the request at
    Trip Story render time. Without this, editing min_star_rating after a
    check makes app/story.py re-filter old raw data against a filter that
    wasn't the one actually used, and the real "Picked" hotel can silently
    vanish from its own candidate list (audit finding #8). Nullable since
    every observation taken before this column existed has no recorded
    value - treated as "no filter was recorded" (0), not an error.
    """
    min_star_rating_used = Column(Integer, nullable=True)

    request = relationship("TripRequest")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    """
    index=True: routers/check.py checks "does any notification exist for
    this request" on every single price check.
    """
    request_id = Column(Integer, ForeignKey("trip_requests.id"), nullable=False, index=True)
    observation_id = Column(Integer, ForeignKey("price_observations.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    """
    The real hold (Sec. 08): set when this notification is reviewed -
    held_observation_id is the freshly re-checked observation whose price
    is frozen, held_until is when that freeze expires. Both null until the
    first review. A booking attempt after held_until must be rejected, not
    silently honored at a stale price - see routers/booking.py.
    """
    held_observation_id = Column(Integer, ForeignKey("price_observations.id"), nullable=True)
    held_until = Column(DateTime(timezone=True), nullable=True)

    request = relationship("TripRequest")
    observation = relationship("PriceObservation", foreign_keys=[observation_id])
    held_observation = relationship("PriceObservation", foreign_keys=[held_observation_id])


class BookingAttempt(Base):
    __tablename__ = "booking_attempts"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("trip_requests.id"), nullable=False)
    """
    unique=True is the real idempotency guarantee - the application-level
    check in routers/booking.py handles the common case, but only a DB
    constraint is actually atomic under two near-simultaneous requests.
    """
    notification_id = Column(
        Integer, ForeignKey("notifications.id"), nullable=False, unique=True
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    accepted_total = Column(Numeric(10, 2), nullable=False)

    flight_status = Column(String, nullable=False, default="pending")
    hotel_status = Column(String, nullable=False, default="pending")
    cab_status = Column(String, nullable=False, default="pending")
    """
    "pending" | "confirmed" | "failed" | "cancelled" per component -
    "cancelled" is new in V2: a component that booked successfully, then
    got a compensating cancellation because a later component failed.
    Aggregate mirrors them: "confirmed" only if all three are confirmed;
    "partial" is V2's real failure-scenario result - a schema-forward value
    from V1 that's now actually produced.
    """
    aggregate_status = Column(String, nullable=False, default="pending")

    supplier_ref_flight = Column(String, nullable=True)
    supplier_ref_hotel = Column(String, nullable=True)
    supplier_ref_cab = Column(String, nullable=True)

    """
    V7: when any component/aggregate status on this row last changed -
    set on every mutation in routers/booking.py. A booking that went
    pending -> in_progress (crashed) -> resumed -> confirmed otherwise
    shows up in the Ops timeline as a single line with no sense that
    anything happened in between (audit finding #7); a second, distinct
    "last changed" timeline event is only possible once this is tracked.
    """
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    request = relationship("TripRequest")
    notification = relationship("Notification")
