from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BookingAttempt, Notification, TripRequest
from app.ownership import get_owned_request
from app.schemas import TripRequestCreate, TripRequestOut, TripRequestUpdate
from app.sim_clock import sim_clock
from app.validation import validate_date_order

router = APIRouter(prefix="/api/requests", tags=["requests"])


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
    return trip_request


@router.get("", response_model=list[TripRequestOut])
def list_requests(user_id: int, db: Session = Depends(get_db)):
    return (
        db.query(TripRequest)
        .filter(TripRequest.user_id == user_id)
        .order_by(TripRequest.id)
        .all()
    )


@router.get("/{request_id}", response_model=TripRequestOut)
def get_request(request_id: int, user_id: int, db: Session = Depends(get_db)):
    return get_owned_request(request_id, user_id, db)


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
    return trip_request


@router.post("/{request_id}/pause", response_model=TripRequestOut)
def pause_request(request_id: int, user_id: int, db: Session = Depends(get_db)):
    trip_request = get_owned_request(request_id, user_id, db)
    trip_request.status = "paused"
    """Pausing should invalidate stale offers same as editing does."""
    _invalidate_stale_offers(request_id, db)
    db.commit()
    db.refresh(trip_request)
    return trip_request


@router.post("/{request_id}/cancel", response_model=TripRequestOut)
def cancel_request(request_id: int, user_id: int, db: Session = Depends(get_db)):
    trip_request = get_owned_request(request_id, user_id, db)
    trip_request.status = "cancelled"
    _invalidate_stale_offers(request_id, db)
    db.commit()
    db.refresh(trip_request)
    return trip_request


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
    return trip_request
