from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Notification, PriceObservation, TripRequest
from app.monitoring import HOLD_DURATION_MINUTES, create_observation
from app.ownership import get_owned_notification
from app.schemas import NotificationOut, NotificationReviewOut
from app.sim_clock import sim_clock

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(user_id: int, db: Session = Depends(get_db)):
    # Scoped to the owner's *active* requests only (audit finding #0) - a
    # paused/cancelled request's old alerts are no longer anything to act
    # on, and showing them invited reviewing/booking a trip the user
    # explicitly said they didn't want anymore.
    #
    # Joins in the request's route and the alerting observation's own total/
    # status (audit finding #5 - Sec. 07 asks for itinerary, itemized total
    # and quote status here, not just observation time) - a plain
    # `from_attributes` pass-through of the Notification row alone can't
    # produce these, so each result row is built explicitly below.
    rows = (
        db.query(Notification, TripRequest, PriceObservation)
        .join(TripRequest, Notification.request_id == TripRequest.id)
        .join(PriceObservation, Notification.observation_id == PriceObservation.id)
        .filter(TripRequest.user_id == user_id, TripRequest.status == "active")
        .order_by(Notification.id)
        .all()
    )
    return [
        NotificationOut(
            id=notification.id,
            request_id=notification.request_id,
            observation_id=notification.observation_id,
            created_at=notification.created_at,
            reviewed_at=notification.reviewed_at,
            held_observation_id=notification.held_observation_id,
            held_until=notification.held_until,
            origin=trip_request.origin,
            destination=trip_request.destination,
            total_price=observation.total_price,
            quote_status=observation.status,
        )
        for notification, trip_request, observation in rows
    ]


@router.post("/{notification_id}/review", response_model=NotificationReviewOut)
def review_notification(notification_id: int, user_id: int, db: Session = Depends(get_db)):
    notification = get_owned_notification(notification_id, user_id, db)

    original_observation = (
        db.query(PriceObservation)
        .filter(PriceObservation.id == notification.observation_id)
        .first()
    )
    trip_request = (
        db.query(TripRequest).filter(TripRequest.id == notification.request_id).first()
    )

    # Audit finding #0: this was the one place in the whole review/book
    # chain that never checked the request was still active - a paused or
    # cancelled request's old alert could still be reviewed (spending a real
    # supplier call) and then booked. check.py's manual check already
    # enforces this same rule; this closes the other door into the same
    # underlying mistake.
    if trip_request.status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Request is {trip_request.status}, not active - this offer can no longer be reviewed or booked.",
        )

    # "Opening an offer must fetch or simulate fresh quotes and recheck
    # availability" (Sec. 08) - a real new check, not a cached read.
    current_observation = create_observation(trip_request, db)

    notification.reviewed_at = sim_clock.get_now()
    if current_observation.status == "complete":
        # The real hold: this specific observation's price is frozen until
        # held_until, regardless of what a later check finds. Only a
        # complete package is worth holding - nothing to freeze otherwise.
        notification.held_observation_id = current_observation.id
        notification.held_until = sim_clock.get_now() + timedelta(minutes=HOLD_DURATION_MINUTES)
    else:
        # A re-check that comes back incomplete invalidates any prior hold -
        # there's no valid price left to honor.
        notification.held_observation_id = None
        notification.held_until = None

    db.commit()
    db.refresh(notification)

    return NotificationReviewOut(
        notification=notification,
        original_observation=original_observation,
        current_observation=current_observation,
    )
