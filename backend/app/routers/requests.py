from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BookingAttempt, Notification, TripRequest
from app.ownership import get_owned_request
from app.schemas import TripRequestCreate, TripRequestOut, TripRequestUpdate
from app.sim_clock import sim_clock
from app.validation import validate_date_order

router = APIRouter(prefix="/api/requests", tags=["requests"])

"""
The three demo requests' exact Sec. 02 seed values (scripts/seed.py) -
keyed by request_id, which is stable across any clean reset since the
three users/requests are always created in the same order. Backs the
"Return to default" button: lets the UI tell whether a request has drifted
from its original demo state, and restore it exactly if so.
"""
SEED_DEFAULTS: dict[int, dict] = {
    1: {
        "origin": "Mumbai",
        "destination": "Goa",
        "outbound_date": date(2026, 12, 26),
        "return_date": date(2026, 12, 29),
        "adults": 2,
        "rooms": 1,
        "budget_inr": 35000,
        "max_stops_outbound": 2,
        "max_stops_return": 2,
        "min_star_rating": 0,
        "checked_baggage": False,
    },
    2: {
        "origin": "Delhi",
        "destination": "Goa",
        "outbound_date": date(2026, 12, 26),
        "return_date": date(2026, 12, 29),
        "adults": 4,
        "rooms": 2,
        "budget_inr": 65000,
        "max_stops_outbound": 2,
        "max_stops_return": 2,
        "min_star_rating": 0,
        "checked_baggage": False,
    },
    3: {
        "origin": "Mumbai",
        "destination": "Jaipur",
        "outbound_date": date(2026, 12, 26),
        "return_date": date(2026, 12, 28),
        "adults": 2,
        "rooms": 1,
        "budget_inr": 30000,
        "max_stops_outbound": 2,
        "max_stops_return": 2,
        "min_star_rating": 0,
        "checked_baggage": False,
    },
}


def _has_drifted_from_default(trip_request: TripRequest) -> bool:
    defaults = SEED_DEFAULTS.get(trip_request.id)
    if defaults is None:
        return False
    if trip_request.status == "cancelled":
        return True
    for field, default_value in defaults.items():
        current_value = getattr(trip_request, field)
        """budget_inr is stored as Numeric - compare as float so a
        value saved as 35000.0 doesn't look "different" from 35000."""
        if field == "budget_inr":
            if float(current_value) != float(default_value):
                return True
        elif current_value != default_value:
            return True
    return False


def _attach_drift_flag(trip_request: TripRequest) -> TripRequest:
    """TripRequestOut reads has_drifted_from_default off the object via
    from_attributes - it isn't a real column, so it has to be set here
    before serialization."""
    trip_request.has_drifted_from_default = _has_drifted_from_default(trip_request)
    return trip_request


def _invalidate_stale_offers(request_id: int, db: Session) -> None:
    """
    Editing a request invalidates its old held offers - they no longer
    describe the trip the user wants. Clearing the hold means a booking
    attempt against it just hits the normal "no active hold" rejection.
    Also resets last_alerted_total so alerts compare against the edited
    numbers, not stale ones.
    """
    already_booked_notification_ids = {
        b.notification_id for b in db.query(BookingAttempt.notification_id)
        .filter(BookingAttempt.request_id == request_id)
        .all()
    }
    stale_notifications = (
        db.query(Notification)
        .filter(
            Notification.request_id == request_id,
            Notification.held_until.isnot(None),
        )
        .all()
    )
    for notification in stale_notifications:
        if notification.id in already_booked_notification_ids:
            """already booked - that's history, not a live offer to invalidate"""
            continue
        notification.held_observation_id = None
        notification.held_until = None

    trip_request = db.query(TripRequest).filter(TripRequest.id == request_id).first()
    if trip_request is not None:
        trip_request.last_alerted_total = None


@router.post("", response_model=TripRequestOut)
def create_request(payload: TripRequestCreate, db: Session = Depends(get_db)):
    validate_date_order(payload.outbound_date, payload.return_date)
    trip_request = TripRequest(**payload.model_dump())
    db.add(trip_request)
    db.commit()
    db.refresh(trip_request)
    return _attach_drift_flag(trip_request)


@router.get("", response_model=list[TripRequestOut])
def list_requests(user_id: int, db: Session = Depends(get_db)):
    requests = (
        db.query(TripRequest)
        .filter(TripRequest.user_id == user_id)
        .order_by(TripRequest.id)
        .all()
    )
    return [_attach_drift_flag(r) for r in requests]


@router.get("/{request_id}", response_model=TripRequestOut)
def get_request(request_id: int, user_id: int, db: Session = Depends(get_db)):
    return _attach_drift_flag(get_owned_request(request_id, user_id, db))


@router.patch("/{request_id}", response_model=TripRequestOut)
def update_request(
    request_id: int, user_id: int, payload: TripRequestUpdate, db: Session = Depends(get_db)
):
    trip_request = get_owned_request(request_id, user_id, db)

    """
    Cancelled requests can't come back (see reactivate_request below), so
    editing one would be a pointless no-op. Paused is still editable since
    it's meant to come back.
    """
    if trip_request.status == "cancelled":
        raise HTTPException(
            status_code=400, detail="A cancelled request cannot be edited."
        )

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(trip_request, field, value)

    if "outbound_date" in updates or "return_date" in updates:
        """
        Validate against the merged result, not just the fields in this
        PATCH - a PATCH that only changes return_date still needs to be
        rejected if it lands before the existing outbound_date.
        """
        try:
            validate_date_order(trip_request.outbound_date, trip_request.return_date)
        except HTTPException:
            db.rollback()
            raise

    if updates:
        _invalidate_stale_offers(request_id, db)
        """Lets the Dashboard tell a current total from one that predates this edit."""
        trip_request.updated_at = sim_clock.get_now()

    db.commit()
    db.refresh(trip_request)
    return _attach_drift_flag(trip_request)


@router.post("/{request_id}/pause", response_model=TripRequestOut)
def pause_request(request_id: int, user_id: int, db: Session = Depends(get_db)):
    trip_request = get_owned_request(request_id, user_id, db)
    trip_request.status = "paused"
    """Pausing should invalidate stale offers same as editing does."""
    _invalidate_stale_offers(request_id, db)
    db.commit()
    db.refresh(trip_request)
    return _attach_drift_flag(trip_request)


@router.post("/{request_id}/cancel", response_model=TripRequestOut)
def cancel_request(request_id: int, user_id: int, db: Session = Depends(get_db)):
    trip_request = get_owned_request(request_id, user_id, db)
    trip_request.status = "cancelled"
    _invalidate_stale_offers(request_id, db)
    db.commit()
    db.refresh(trip_request)
    return _attach_drift_flag(trip_request)


@router.post("/{request_id}/reactivate", response_model=TripRequestOut)
def reactivate_request(request_id: int, user_id: int, db: Session = Depends(get_db)):
    """
    Not explicitly required by the brief, but pausing without a way back
    would make "paused" a dead end rather than a real, reversible state.
    """
    trip_request = get_owned_request(request_id, user_id, db)
    if trip_request.status == "cancelled":
        raise HTTPException(status_code=400, detail="A cancelled request cannot be reactivated.")
    trip_request.status = "active"
    db.commit()
    db.refresh(trip_request)
    return _attach_drift_flag(trip_request)


@router.post("/{request_id}/reset-to-default", response_model=TripRequestOut)
def reset_request_to_default(request_id: int, user_id: int, db: Session = Depends(get_db)):
    """
    Restores one of the three demo requests to its exact Sec. 02 seed
    values - lets a reviewer undo any edits/pause/cancel made while poking
    around, without needing a full database reset. Only defined for the
    three known demo requests; anything else is a 404.
    """
    trip_request = get_owned_request(request_id, user_id, db)
    defaults = SEED_DEFAULTS.get(request_id)
    if defaults is None:
        raise HTTPException(status_code=404, detail="No default state known for this request.")

    for field, value in defaults.items():
        setattr(trip_request, field, value)
    trip_request.status = "active"
    _invalidate_stale_offers(request_id, db)
    trip_request.updated_at = sim_clock.get_now()

    db.commit()
    db.refresh(trip_request)
    return _attach_drift_flag(trip_request)
