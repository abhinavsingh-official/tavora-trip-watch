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
    Bounds below are basic input sanity (Sec. 03/05), not a market-realism
    claim - date ordering (the thing that actually made a trip nonsensical
    rather than just unusual) is checked separately in app/validation.py,
    since Pydantic field constraints can't compare two sibling fields.
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
    Every field optional - a PATCH only changes what's actually sent.
    Status is deliberately NOT editable here - pause/cancel/reactivate go
    through their own explicit endpoints, not a generic field update, so
    each has its own clear audit trail and can't be silently smuggled in
    alongside an unrelated budget edit.
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
    V7, audit finding #1: when the request's own fields last changed -
    compared against a PriceObservation's own `observed_at` on the
    frontend to flag a displayed total as stale.
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
    V7, audit finding #5: Sec. 07 explicitly asks the notification to
    "Include itinerary, itemized total, observation time, quote status" -
    previously only observation time was shown, and every alert rendered
    as an indistinguishable "Request #N". Populated explicitly in
    list_notifications (not every field comes straight off the
    Notification row itself, so this can't be a plain from_attributes
    pass-through).
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
    V2: the server derives the authoritative total from the held
    observation itself (see routers/booking.py), not from a client-
    supplied number - a real correctness tightening over V1, which trusted
    whatever the frontend echoed back.
    """
    notification_id: int


class LabFailComponentIn(BaseModel):
    request_id: int
    component: str
    """
    "fail" (default, V2) | "unavailable" (Sec. 09 row 2 - inventory
    disappeared) | "timeout" (Sec. 09 row 4 - supplier response never
    resolves, leaves the component "unknown" until reconciled).
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
    "confirmed" | "failed" - what actually happened with the supplier,
    discovered after a simulated timeout (Sec. 09 row 4).
    """
    outcome: str


class LabAdvanceClockIn(BaseModel):
    minutes: float


class LabTriggerCycleOut(BaseModel):
    checked_request_ids: list[int]


class TimelineEventOut(BaseModel):
    """
    One merged, time-ordered feed of everything that happened on a
    request - observations, notifications, booking attempts - so the Ops
    view can show "what happened, in order" for a stuck request, not three
    separate lists the viewer has to mentally interleave themselves.
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
    Sec. 11 scenario 4: registers a small set of requests against one
    shared, finite room counter - at most one of them can successfully
    confirm its hotel component while the counter has rooms left (see
    routers/booking.py's _try_claim_shared_room). Replaces any previously
    active pool, keeping this a one-scenario-at-a-time Lab control.
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
