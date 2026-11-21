from datetime import datetime

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


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


class TripRequest(Base):
    __tablename__ = "trip_requests"

    id = Column(Integer, primary_key=True)
    # Postgres does not auto-index foreign keys (only primary keys) -
    # index=True here matters once a user has more than a handful of
    # requests, since every Dashboard load filters on this column.
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
    # "active" is the only status V1 acts on; "paused"/"cancelled" exist now so
    # V3's edit/pause/cancel work needs no schema change later.
    status = Column(String, nullable=False, default="active")

    user = relationship("User")


class PriceObservation(Base):
    __tablename__ = "price_observations"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("trip_requests.id"), nullable=False)
    observed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    # A composite index matching the actual query shape (routers/check.py's
    # list_observations: filter by request_id, order by observed_at desc) -
    # this will matter once the V2 scheduler starts appending rows every 5
    # minutes; invisible at today's row counts but worth having from day one
    # rather than retrofitting once it's already slow.
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
    # Package-level status: "complete" only if every component above is
    # "complete"; otherwise "provisional" (something's missing/approximate but
    # present) or "unavailable" (a component couldn't be fetched at all).
    # Only "complete" can ever trigger a budget alert (assignment Sec. 05).
    status = Column(String, nullable=False, default="unavailable")

    # The full raw response from each real source call that produced this
    # observation - kept for traceability and the data-source dossier's
    # "sanitized sample data" / field-mapping requirement. Null for cabs
    # (simulated, no external response to keep).
    raw_sources = Column(JSONB, nullable=True)

    request = relationship("TripRequest")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    # index=True: routers/check.py checks "does any notification exist for
    # this request" on every single price check.
    request_id = Column(Integer, ForeignKey("trip_requests.id"), nullable=False, index=True)
    observation_id = Column(Integer, ForeignKey("price_observations.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    request = relationship("TripRequest")
    observation = relationship("PriceObservation")


class BookingAttempt(Base):
    __tablename__ = "booking_attempts"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("trip_requests.id"), nullable=False)
    # unique=True is the real idempotency guarantee - the application-level
    # check in routers/booking.py handles the common case, but only a DB
    # constraint is actually atomic under two near-simultaneous requests.
    notification_id = Column(
        Integer, ForeignKey("notifications.id"), nullable=False, unique=True
    )
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    accepted_total = Column(Numeric(10, 2), nullable=False)

    flight_status = Column(String, nullable=False, default="pending")
    hotel_status = Column(String, nullable=False, default="pending")
    cab_status = Column(String, nullable=False, default="pending")
    # "pending" | "confirmed" | "failed" per component.
    # Aggregate mirrors them: "confirmed" only if all three are confirmed;
    # "partial" exists now so V2's failure-handling has somewhere to put it
    # without a schema change, even though V1 never produces it.
    aggregate_status = Column(String, nullable=False, default="pending")

    supplier_ref_flight = Column(String, nullable=True)
    supplier_ref_hotel = Column(String, nullable=True)
    supplier_ref_cab = Column(String, nullable=True)

    request = relationship("TripRequest")
    notification = relationship("Notification")
