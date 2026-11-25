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
    # Just sanity bounds; date ordering is checked in app/validation.py (sibling fields can't be compared here)
    adults: int = Field(ge=1)
    rooms: int = Field(ge=1)
    budget_inr: float = Field(gt=0)
    max_stops_outbound: int = Field(2, ge=0)
    max_stops_return: int = Field(2, ge=0)
    min_star_rating: int = Field(0, ge=0, le=5)
    checked_baggage: bool = False


class TripRequestUpdate(BaseModel):
    # All fields optional (PATCH sends only what changed); status changes use their own endpoints
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
    # Frontend compares against an observation's observed_at to flag a displayed total as stale
    updated_at: datetime
    # True if edited from seed values; drives "Return to default" (computed per response, not stored)
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
    held_until_flight: datetime | None
    held_until_hotel: datetime | None
    held_until_cab: datetime | None
    # Not a real column - the earliest of the three above, i.e. the moment the offer as a whole
    # stops being fully bookable. Kept for the frontend's one countdown; see held_until_* for detail.
    held_until: datetime | None
    # Not on the Notification row itself; built explicitly in list_notifications
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
    # Server computes the total from the held observation, ignoring whatever the client sends
    notification_id: int


class LabFailComponentIn(BaseModel):
    request_id: int
    component: str
    outcome: str = "fail"  # "fail" | "unavailable" | "timeout" (stays "unknown" until reconciled)


class LabCancelFailureIn(BaseModel):
    request_id: int
    component: str


class LabRestartAfterIn(BaseModel):
    request_id: int
    component: str


class LabPriceCheckTimeoutIn(BaseModel):
    request_id: int
    component: str


class BookingReconcileIn(BaseModel):
    outcome: str  # "confirmed" | "failed" - the supplier's real outcome after a simulated timeout


class LabAdvanceClockIn(BaseModel):
    minutes: float


class LabTriggerCycleOut(BaseModel):
    checked_request_ids: list[int]


class TimelineEventOut(BaseModel):
    # Merged, time-ordered feed of observations/notifications/bookings for the Ops view
    type: str  # "observation" | "notification" | "booking"
    at: datetime
    summary: str


class LabOverrideIn(BaseModel):
    request_id: int
    component: str
    price: float


class LabSharedRoomScenarioIn(BaseModel):
    # Registers requests against one shared room counter, replacing any active pool (see booking.py)
    request_ids: list[int]
    rooms_remaining: int


class LabClockOut(BaseModel):
    now: datetime


class LabBookNowIn(BaseModel):
    request_id: int


class LabShockIn(BaseModel):
    request_id: int
    """-0.6..0.6 - how hard to shock this trip's own market, and which way. Clamped server-side too."""
    shock_fraction: float


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
    observation_id: int  # which observation this was built from, so staleness is checkable
    observed_at: datetime
    outbound_flight_candidates: list[FlightCandidateOut]
    return_flight_candidates: list[FlightCandidateOut]
    hotel_candidates: list[HotelCandidateOut]
    cab: CabQuoteOut


class FlightDirectoryCandidateOut(BaseModel):
    carrier_code: str
    carrier_name: str
    flight_number: int
    departure_time: str
    arrival_time: str
    stops: int
    price_inr: float
    selected: bool


class HotelDirectoryCandidateOut(BaseModel):
    hotel_name: str
    category_name: str | None
    star_rating: int
    room_description: str | None
    price_inr: float
    selected: bool


class CabDirectoryCandidateOut(BaseModel):
    vendor_name: str
    vehicle_class: str
    passenger_capacity: int
    luggage_capacity: int
    distance_km: float
    per_km_rate_inr: float
    price_per_leg_inr: float
    selected: bool


class TripDirectoryOut(BaseModel):
    # Live candidates straight from source tables, not a snapshot; "selected" matches pricing.py's current pick
    outbound_flight_candidates: list[FlightDirectoryCandidateOut]
    return_flight_candidates: list[FlightDirectoryCandidateOut]
    hotel_candidates: list[HotelDirectoryCandidateOut]
    cab_candidates: list[CabDirectoryCandidateOut]


class SharedRoomRaceEntryOut(BaseModel):
    request_id: int
    origin: str
    destination: str
    hotel_status: str | None  # null if this request hasn't attempted a booking yet
    aggregate_status: str | None


class SharedRoomStatusOut(BaseModel):
    rooms_remaining: int
    entries: list[SharedRoomRaceEntryOut]
