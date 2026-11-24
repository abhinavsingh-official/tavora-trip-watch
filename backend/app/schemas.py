from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


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
    """
    These are just sanity bounds, not realistic-trip checks. Date ordering
    is handled in app/validation.py instead, since Pydantic field
    constraints can't compare two sibling fields.
    """
    adults: int = Field(ge=1)
    rooms: int = Field(ge=1)
    budget_inr: float = Field(gt=0)
    max_stops_outbound: int = Field(2, ge=0)
    max_stops_return: int = Field(2, ge=0)
    min_star_rating: int = Field(0, ge=0, le=5)
    checked_baggage: bool = False


class TripRequestUpdate(BaseModel):
    """
    Every field optional since PATCH only sends what changed. No status
    field - pause/cancel/reactivate go through their own endpoints so they
    don't get smuggled in with an unrelated edit.
    """
    origin: str | None = None
    destination: str | None = None
    outbound_date: date | None = None
    return_date: date | None = None
    adults: int | None = Field(default=None, ge=1)
    rooms: int | None = Field(default=None, ge=1)
    budget_inr: float | None = Field(default=None, gt=0)
    max_stops_outbound: int | None = Field(default=None, ge=0)
    max_stops_return: int | None = Field(default=None, ge=0)
    min_star_rating: int | None = Field(default=None, ge=0, le=5)
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
    """
    Frontend compares this against an observation's observed_at to flag a
    displayed total as stale.
    """
    updated_at: datetime
    """
    True if this request's editable fields (or status) differ from its
    original seed values - drives the "Return to default" button, which
    only shows up once there's actually something to reset. Computed per
    response, not a stored column - see routers/requests.py.
    """
    has_drifted_from_default: bool = False


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
    """
    Notification needs the itinerary, total, and quote status, not just the
    timestamp - built explicitly in list_notifications since these fields
    don't live on the Notification row itself.
    """
    origin: str
    destination: str
    total_price: float | None
    quote_status: str


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
    """
    Server computes the total from the held observation, not from
    whatever the client sends.
    """
    notification_id: int


class LabFailComponentIn(BaseModel):
    request_id: int
    component: str
    """
    "fail" (default) | "unavailable" (inventory disappeared) | "timeout"
    (supplier never responds, component stays "unknown" until reconciled).
    """
    outcome: str = "fail"


class LabCancelFailureIn(BaseModel):
    request_id: int
    component: str


class LabRestartAfterIn(BaseModel):
    request_id: int
    component: str


class BookingReconcileIn(BaseModel):
    """
    "confirmed" | "failed" - what the supplier actually did, found out
    after a simulated timeout.
    """
    outcome: str


class LabAdvanceClockIn(BaseModel):
    minutes: float


class LabTriggerCycleOut(BaseModel):
    checked_request_ids: list[int]


class TimelineEventOut(BaseModel):
    """
    One merged, time-ordered feed of observations, notifications, and
    booking attempts, so the Ops view can show what happened to a stuck
    request in order instead of three lists to cross-reference.
    """
    """'observation' | 'notification' | 'booking'"""
    type: str
    at: datetime
    summary: str


class LabOverrideIn(BaseModel):
    request_id: int
    component: str
    price: float


class LabSharedRoomScenarioIn(BaseModel):
    """
    Registers a set of requests against one shared, finite room counter -
    see _try_claim_shared_room in routers/booking.py. Replaces whatever
    pool was active before; only one scenario can run at a time.
    """
    request_ids: list[int]
    rooms_remaining: int


class LabClockOut(BaseModel):
    now: datetime


class FlightCandidateOut(BaseModel):
    carrier_code: str | None
    flight_number: int | None
    departure_airport: str | None
    arrival_airport: str | None
    departure_time: str | None
    arrival_time: str | None
    stops: int
    price_inr: float
    selected: bool


class HotelCandidateOut(BaseModel):
    name: str | None
    category_name: str | None
    stars: int
    price_inr: float
    selected: bool


class CabQuoteOut(BaseModel):
    outbound_price: float | None
    return_price: float | None
    status: str


class TripStoryOut(BaseModel):
    """
    Which observation this story was built from - the Trip Story page
    always reads the latest one, but surfacing the id makes "is this
    fresh" checkable rather than implicit.
    """
    observation_id: int
    observed_at: datetime
    outbound_flight_candidates: list[FlightCandidateOut]
    return_flight_candidates: list[FlightCandidateOut]
    hotel_candidates: list[HotelCandidateOut]
    cab: CabQuoteOut
