from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Notification, PriceObservation, TripRequest
from app.routers.check import _create_observation
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
def review_notification(notification_id: int, db: Session = Depends(get_db)):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")

    original_observation = (
        db.query(PriceObservation)
        .filter(PriceObservation.id == notification.observation_id)
        .first()
    )
    trip_request = (
        db.query(TripRequest).filter(TripRequest.id == notification.request_id).first()
    )

    current_observation = _create_observation(trip_request, db)

    notification.reviewed_at = sim_clock.get_now()
    db.commit()
    db.refresh(notification)

    return NotificationReviewOut(
        notification=notification,
        original_observation=original_observation,
        current_observation=current_observation,
    )
