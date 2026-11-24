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
    """
    Timezone-aware, not datetime.utcnow(). Paired with the
    DateTime(timezone=True) columns below so every timestamp serializes
    with an explicit UTC offset - a naive one gets misread as local time
    by the browser, which once made a brand-new hold look already expired.
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
    Postgres doesn't auto-index foreign keys, and every dashboard load
    filters on this column, so index=True earns its keep.
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
    "active" is the only status we act on right now; "paused"/"cancelled"
    are here so edit/pause/cancel doesn't need a migration later.
    """
    status = Column(String, nullable=False, default="active")

    """
    Null means no active alert - either never crossed under budget, or
    crossed back over and reset. Otherwise it's the total we last alerted
    at, so we know whether a further drop is big enough (5%+) to re-alert
    or should just stay quiet.
    """
    last_alerted_total = Column(Numeric(10, 2), nullable=True)

    """
    When this request's own fields last changed (create or edit) - pause/
    cancel/reactivate don't touch it, those are status transitions, not
    edits. Lets the dashboard tell "this total is current" from "this
    total predates your last edit".
    """
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    user = relationship("User")


class PriceObservation(Base):
    __tablename__ = "price_observations"

    id = Column(Integer, primary_key=True)
    request_id = Column(Integer, ForeignKey("trip_requests.id"), nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    """
    Composite index matching the actual query in routers/check.py
    (filter by request_id, order by observed_at desc). Doesn't matter at
    today's row counts, will once the scheduler is appending rows every
    5 minutes.
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
    too; otherwise "provisional" (something's missing/approximate) or
    "unavailable" (a component couldn't be fetched at all). Only
    "complete" can trigger a budget alert.
    """
    status = Column(String, nullable=False, default="unavailable")

    """
    Raw response from each real source call, kept for traceability.
    Null for cabs since there's no external response to keep.
    """
    raw_sources = Column(JSONB, nullable=True)

    """
    The min-star filter actually in effect when this check ran, captured
    here instead of re-read off the request later. Otherwise editing
    min_star_rating after a check makes story.py re-filter old data with
    the wrong filter, and the picked hotel can vanish from its own
    candidate list. Null just means no filter was recorded (treat as 0).
    """
    min_star_rating_used = Column(Integer, nullable=True)

    request = relationship("TripRequest")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    """
    index=True: check.py checks whether a notification already exists
    for this request on every price check.
    """
    request_id = Column(Integer, ForeignKey("trip_requests.id"), nullable=False, index=True)
    observation_id = Column(Integer, ForeignKey("price_observations.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)

    """
    Set once this notification is reviewed: held_observation_id is the
    re-checked observation whose price gets frozen, held_until is when
    that freeze expires. A booking after held_until must be rejected,
    not honored at a stale price - see booking.py.
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
    unique=True is the actual idempotency guard - the app-level check in
    booking.py covers the common case, but only a DB constraint is
    atomic under two near-simultaneous requests.
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
    "cancelled" means it booked fine, then got rolled back because
    another component failed. Aggregate is "confirmed" only if all three
    are; "partial" is the real failure case.
    """
    aggregate_status = Column(String, nullable=False, default="pending")

    supplier_ref_flight = Column(String, nullable=True)
    supplier_ref_hotel = Column(String, nullable=True)
    supplier_ref_cab = Column(String, nullable=True)

    """
    When any status on this row last changed, set on every mutation in
    booking.py. Without it a booking that went pending -> stuck ->
    resumed -> confirmed just shows up as one flat line in the Ops
    timeline.
    """
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    request = relationship("TripRequest")
    notification = relationship("Notification")


class CachedHotelOption(Base):
    """
    A real Hotelbeds result, pre-fetched by scripts/fetch_hotel_directory.py
    (fallback sandbox account, so it doesn't eat into the live 50/day
    quota) and cached so we can show a real hotel directory without
    re-hitting Hotelbeds on every check. hotels.py reads this table
    first; an uncached search falls back to a live call, or
    "unavailable" - never a made-up price.
    """

    __tablename__ = "cached_hotel_options"

    id = Column(Integer, primary_key=True)
    """
    Must match a TripRequest's (destination, outbound_date, return_date,
    rooms, adults) for hotels.py to use this row instead of a live call.
    """
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
    """The real fetched rate, never changes after insert. price_eur is
    what pricing actually reads, nudged over time by price_mutation.py
    and clamped back toward this anchor."""
    base_price_eur = Column(Float, nullable=False)
    price_eur = Column(Float, nullable=False)

    fetched_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    """
    Always "real-sandbox:hotelbeds-fallback-seed" today - kept as a
    column rather than hardcoded in case a future refresh uses a
    different source.
    """
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
    """
    Sabre's sandbox only ever returns one static test fare, so it can't
    show real price movement. This table is what the product actually
    uses: a bigger, realistic directory (same route/airport shape Sabre
    gave us), with current_price_inr nudged over time by
    mutate_prices.py so repeat checks look like a real market. Always
    labeled synthetic, never passed off as a live feed.
    """

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
    """Mutated by mutate_prices.py - pricing.py reads this, not
    base_price_inr."""
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
    """
    Cabs have no real fare source we could find (see cabs.py). This
    replaces the old flat formula with a small directory of vehicle
    classes anchored to the same RTO rate cards cabs.py cites -
    passenger/luggage capacity are real constraints, not decoration.
    Route-agnostic since price depends on vehicle class, not city -
    every class assumes the same representative one-way transfer
    distance, so the price is distance_km * per_km_rate_inr, not a
    flat guess (see generate_synthetic_data.py).
    """

    __tablename__ = "synthetic_cab_options"

    id = Column(Integer, primary_key=True)
    vendor_name = Column(String, nullable=False)
    vehicle_class = Column(String, nullable=False)
    passenger_capacity = Column(Integer, nullable=False)
    """0 = no luggage space (e.g. auto-rickshaw class, not actually
    offered here) - every class we do offer has some capacity."""
    luggage_capacity = Column(Integer, nullable=False)

    distance_km = Column(Float, nullable=False, default=30.0)
    per_km_rate_inr = Column(Float, nullable=False, default=20.0)

    base_price_per_leg_inr = Column(Float, nullable=False)
    current_price_per_leg_inr = Column(Float, nullable=False)
    last_mutated_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    source = Column(String, nullable=False, default="simulated")


class SimulationLogEntry(Base):
    """
    The visible evidence trail for the Simulation: every price check,
    booking attempt, and Lab action writes a plain-language row here -
    who/what/how much/real-or-simulated/how it ended - so a reviewer
    doesn't have to read code to see something actually happened. See
    simulation_log.py for the writer; lab.py exposes it read-only.
    """

    __tablename__ = "simulation_log_entries"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow, index=True)
    request_id = Column(Integer, ForeignKey("trip_requests.id"), nullable=True)
    """Denormalized at write time, so the log still reads right even if
    the request is later edited or cancelled, and listing recent
    entries doesn't need a join."""
    user_name = Column(String, nullable=True)
    route_label = Column(String, nullable=True)

    event_type = Column(String, nullable=False)
    summary = Column(String, nullable=False)

    flight_name = Column(String, nullable=True)
    hotel_name = Column(String, nullable=True)
    cab_name = Column(String, nullable=True)
    total_cost_inr = Column(Numeric(10, 2), nullable=True)

    is_simulated = Column(Boolean, nullable=False, default=True)
    """"finished" | "failed" | "unfinished" | "info" """
    status = Column(String, nullable=False, default="info")
    duration_ms = Column(Integer, nullable=True)

    request = relationship("TripRequest")


class SharedRoomPool(Base):
    """
    Lab-only construct for the "last room" race scenario: nothing in the
    real or synthetic hotel data is a shared resource two requests can
    contend over (each request's search is independent). Here a handful
    of request IDs share one counter, decremented atomically in
    booking.py's _try_claim_shared_room - only one request can win once
    it hits zero.
    """

    __tablename__ = "shared_room_pools"

    id = Column(Integer, primary_key=True)
    label = Column(String, nullable=False, default="Last room demo")
    rooms_remaining = Column(Integer, nullable=False)
    request_ids = Column(JSONB, nullable=False)
