from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class TripRequestCreate(BaseModel):
    user_id: int
    origin: str
    destination: str
    outbound_date: date
    return_date: date
    adults: int
    rooms: int
    budget_inr: float
    max_stops_outbound: int = 2
    max_stops_return: int = 2
    min_star_rating: int = 0
    checked_baggage: bool = False


class TripRequestUpdate(BaseModel):
    # Every field optional - a PATCH only changes what's actually sent.
    # Status is deliberately NOT editable here - pause/cancel/reactivate go
    # through their own explicit endpoints, not a generic field update, so
    # each has its own clear audit trail and can't be silently smuggled in
    # alongside an unrelated budget edit.
    origin: str | None = None
    destination: str | None = None
    outbound_date: date | None = None
    return_date: date | None = None
    adults: int | None = None
    rooms: int | None = None
    budget_inr: float | None = None
    max_stops_outbound: int | None = None
    max_stops_return: int | None = None
    min_star_rating: int | None = None
    checked_baggage: bool | None = None


class TripRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    origin: str
    destination: str
    outbound_date: date
    return_date: date
    adults: int
    rooms: int
    budget_inr: float
    max_stops_outbound: int
    max_stops_return: int
    min_star_rating: int
    checked_baggage: bool
    status: str


class PriceObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    observed_at: datetime
    flight_outbound_price: float | None
    flight_return_price: float | None
    flight_status: str
    hotel_total_price: float | None
    hotel_status: str
    cab_outbound_price: float | None
    cab_return_price: float | None
    cab_status: str
    taxes_fees: float | None
    total_price: float | None
    status: str


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    observation_id: int
    created_at: datetime
    reviewed_at: datetime | None
    held_observation_id: int | None
    held_until: datetime | None


class NotificationReviewOut(BaseModel):
    notification: NotificationOut
    original_observation: PriceObservationOut
    current_observation: PriceObservationOut


class BookingAttemptOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    notification_id: int
    created_at: datetime
    accepted_total: float
    flight_status: str
    hotel_status: str
    cab_status: str
    aggregate_status: str
    supplier_ref_flight: str | None
    supplier_ref_hotel: str | None
    supplier_ref_cab: str | None


class BookingCreateIn(BaseModel):
    # V2: the server derives the authoritative total from the held
    # observation itself (see routers/booking.py), not from a client-
    # supplied number - a real correctness tightening over V1, which trusted
    # whatever the frontend echoed back.
    notification_id: int


class LabFailComponentIn(BaseModel):
    request_id: int
    component: str


class LabAdvanceClockIn(BaseModel):
    minutes: float


class LabTriggerCycleOut(BaseModel):
    checked_request_ids: list[int]


class TimelineEventOut(BaseModel):
    # One merged, time-ordered feed of everything that happened on a
    # request - observations, notifications, booking attempts - so the Ops
    # view can show "what happened, in order" for a stuck request, not three
    # separate lists the viewer has to mentally interleave themselves.
    type: str  # "observation" | "notification" | "booking"
    at: datetime
    summary: str


class LabOverrideIn(BaseModel):
    request_id: int
    component: str
    price: float


class LabClockOut(BaseModel):
    now: datetime
