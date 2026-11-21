from datetime import timedelta

from fastapi import APIRouter, Depends
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
    return (
        db.query(Notification)
        .join(TripRequest, Notification.request_id == TripRequest.id)
        .filter(TripRequest.user_id == user_id)
        .order_by(Notification.id)
        .all()
    )


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
