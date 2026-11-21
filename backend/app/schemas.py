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
    notification_id: int
    accepted_total: float


class LabOverrideIn(BaseModel):
    request_id: int
    component: str
    price: float


class LabClockOut(BaseModel):
    now: datetime
