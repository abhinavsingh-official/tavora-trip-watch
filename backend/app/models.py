from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
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
    """Tz-aware (not utcnow()) so timestamps always carry an explicit UTC offset."""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)


class TripRequest(Base):
    __tablename__ = "trip_requests"

    id = Column(Integer, primary_key=True)
    # Postgres doesn't auto-index FKs, and dashboard loads filter on this column
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
    # Only "active" is acted on; paused/cancelled exist so those actions skip a migration later
    status = Column(String, nullable=False, default="active")

    # Null = no active alert; otherwise the total last alerted at, to gate re-alerts on a further 5%+ drop
    last_alerted_total = Column(Numeric(10, 2), nullable=True)

    # Bumped on field edits only (not status transitions), so the dashboard can flag a stale total
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    user = relationship("User")


class PriceObservation(Base):
    __tablename__ = "price_observations"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("trip_requests.id"), nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    # Composite index matches routers/check.py's actual query (request_id filter, observed_at order)
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
    # "complete" only if every component is too; only "complete" can trigger a budget alert
    status = Column(String, nullable=False, default="unavailable")

    # Raw per-source responses for traceability; null for cabs (no external response to keep)
    raw_sources = Column(JSONB, nullable=True)

    # Filter in effect when this check ran, so a later edit to min_star_rating can't reinterpret old data
    min_star_rating_used = Column(Integer, nullable=True)

    request = relationship("TripRequest")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    # indexed: check.py looks up an existing notification for this request on every price check
    request_id = Column(Integer, ForeignKey("trip_requests.id"), nullable=False, index=True)
    observation_id = Column(Integer, ForeignKey("price_observations.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    # Set once reviewed: freezes the price at held_observation_id until held_until (see booking.py)
    held_observation_id = Column(Integer, ForeignKey("price_observations.id"), nullable=True)
    held_until = Column(DateTime(timezone=True), nullable=True)

    request = relationship("TripRequest")
    observation = relationship("PriceObservation", foreign_keys=[observation_id])
    held_observation = relationship("PriceObservation", foreign_keys=[held_observation_id])


class BookingAttempt(Base):
    __tablename__ = "booking_attempts"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("trip_requests.id"), nullable=False)
    # unique=True is the real idempotency guard; it's atomic under two near-simultaneous requests
    notification_id = Column(
        Integer, ForeignKey("notifications.id"), nullable=False, unique=True
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    accepted_total = Column(Numeric(10, 2), nullable=False)

    flight_status = Column(String, nullable=False, default="pending")
    hotel_status = Column(String, nullable=False, default="pending")
    cab_status = Column(String, nullable=False, default="pending")
    # "cancelled" = booked then rolled back after a sibling failed; "confirmed" needs all three
    aggregate_status = Column(String, nullable=False, default="pending")

    supplier_ref_flight = Column(String, nullable=True)
    supplier_ref_hotel = Column(String, nullable=True)
    supplier_ref_cab = Column(String, nullable=True)

    # Bumped on every mutation in booking.py so the Ops timeline shows the state history, not one flat line
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    request = relationship("TripRequest")
    notification = relationship("Notification")


class CachedHotelOption(Base):
    # Pre-fetched Hotelbeds inventory (sandbox quota); hotels.py falls back to a live call, never a made-up price
    __tablename__ = "cached_hotel_options"

    id = Column(Integer, primary_key=True)
    # Must match a TripRequest's destination/dates/rooms/adults for hotels.py to reuse this row
    destination = Column(String, nullable=False, index=True)
    check_in = Column(Date, nullable=False)
    check_out = Column(Date, nullable=False)
    rooms = Column(Integer, nullable=False)
    adults = Column(Integer, nullable=False)

    hotel_code = Column(Integer, nullable=False)
    hotel_name = Column(String, nullable=False)
    category_name = Column(String, nullable=True)
    star_rating = Column(Integer, nullable=False, default=0)
    room_description = Column(String, nullable=True)
    # Fixed at insert; price_eur is what pricing reads, nudged by price_mutation.py and clamped to this anchor
    base_price_eur = Column(Float, nullable=False)
    price_eur = Column(Float, nullable=False)

    fetched_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    # A column (not hardcoded) in case a future refresh uses a different source
    source = Column(String, nullable=False, default="real-sandbox:hotelbeds-fallback-seed")

    __table_args__ = (
        Index(
            "ix_cached_hotel_options_search_key",
            "destination",
            "check_in",
            "check_out",
            "rooms",
            "adults",
        ),
    )


class SyntheticFlightOption(Base):
    # Sabre's sandbox returns one static fare, so this directory drives realistic price movement instead
    __tablename__ = "synthetic_flight_options"

    id = Column(Integer, primary_key=True)
    origin_code = Column(String, nullable=False, index=True)
    destination_code = Column(String, nullable=False, index=True)
    travel_date = Column(Date, nullable=False, index=True)

    carrier_code = Column(String, nullable=False)
    carrier_name = Column(String, nullable=False)
    flight_number = Column(Integer, nullable=False)
    departure_time = Column(String, nullable=False)
    arrival_time = Column(String, nullable=False)
    stops = Column(Integer, nullable=False, default=0)

    base_price_inr = Column(Float, nullable=False)
    # Mutated by mutate_prices.py; pricing.py reads this, not base_price_inr
    current_price_inr = Column(Float, nullable=False)
    last_mutated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    source = Column(String, nullable=False, default="synthetic")

    __table_args__ = (
        Index(
            "ix_synthetic_flight_options_route_date",
            "origin_code",
            "destination_code",
            "travel_date",
        ),
    )


class SyntheticCabOption(Base):
    # No real cab fare source (see cabs.py); directory of vehicle classes anchored to RTO rate cards
    __tablename__ = "synthetic_cab_options"

    id = Column(Integer, primary_key=True)
    vendor_name = Column(String, nullable=False)
    vehicle_class = Column(String, nullable=False)
    passenger_capacity = Column(Integer, nullable=False)
    # 0 = no luggage space; every class actually offered here has some capacity
    luggage_capacity = Column(Integer, nullable=False)

    distance_km = Column(Float, nullable=False, default=30.0)
    per_km_rate_inr = Column(Float, nullable=False, default=20.0)

    base_price_per_leg_inr = Column(Float, nullable=False)
    current_price_per_leg_inr = Column(Float, nullable=False)
    last_mutated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    source = Column(String, nullable=False, default="simulated")


class SimulationLogEntry(Base):
    # Plain-language evidence trail for the Simulation (see simulation_log.py writer, lab.py reader)
    __tablename__ = "simulation_log_entries"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, index=True)
    request_id = Column(Integer, ForeignKey("trip_requests.id"), nullable=True)
    # Denormalized at write time so the log still reads right if the request is later edited/cancelled
    user_name = Column(String, nullable=True)
    route_label = Column(String, nullable=True)

    event_type = Column(String, nullable=False)
    summary = Column(String, nullable=False)

    flight_name = Column(String, nullable=True)
    hotel_name = Column(String, nullable=True)
    cab_name = Column(String, nullable=True)
    total_cost_inr = Column(Numeric(10, 2), nullable=True)

    is_simulated = Column(Boolean, nullable=False, default=True)
    status = Column(String, nullable=False, default="info")  # "finished" | "failed" | "unfinished" | "info"
    duration_ms = Column(Integer, nullable=True)

    request = relationship("TripRequest")


class SharedRoomPool(Base):
    # Lab-only: a shared, finite room counter for the "last room" race demo (see booking.py _try_claim_shared_room)
    __tablename__ = "shared_room_pools"

    id = Column(Integer, primary_key=True)
    label = Column(String, nullable=False, default="Last room demo")
    rooms_remaining = Column(Integer, nullable=False)
    request_ids = Column(JSONB, nullable=False)
