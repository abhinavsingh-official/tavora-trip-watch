from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
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
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
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
    request_id = Column(Integer, ForeignKey("trip_requests.id"), nullable=False)
    observation_id = Column(Integer, ForeignKey("price_observations.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reviewed_at = Column(DateTime, nullable=True)

    request = relationship("TripRequest")
    observation = relationship("PriceObservation")


class BookingAttempt(Base):
    __tablename__ = "booking_attempts"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("trip_requests.id"), nullable=False)
    notification_id = Column(Integer, ForeignKey("notifications.id"), nullable=False)
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
