from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Notification, PriceObservation, TripRequest
from app.monitoring import clear_component_holds, create_observation, earliest_hold_deadline, set_component_holds
from app.ownership import get_owned_notification
from app.schemas import NotificationOut, NotificationReviewOut
from app.sim_clock import now_for_request

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_notifications(user_id: int, db: Session = Depends(get_db)):
    # Only the latest notification per request - an older, re-alerted-over one is stale by
    # definition (a further price drop already superseded it) and would otherwise sit in the list
    # forever showing a worse number than the current real price, looking like a bug.
    latest_per_request = (
        db.query(func.max(Notification.id).label("id"))
        .join(TripRequest, Notification.request_id == TripRequest.id)
        .filter(TripRequest.user_id == user_id, TripRequest.status == "active")
        .group_by(Notification.request_id)
        .subquery()
    )
    rows = (
        db.query(Notification, TripRequest, PriceObservation)
        .join(TripRequest, Notification.request_id == TripRequest.id)
        .join(PriceObservation, Notification.observation_id == PriceObservation.id)
        .filter(Notification.id.in_(db.query(latest_per_request.c.id)))
        .order_by(Notification.id.desc())
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
            held_until_flight=notification.held_until_flight,
            held_until_hotel=notification.held_until_hotel,
            held_until_cab=notification.held_until_cab,
            held_until=earliest_hold_deadline(notification),
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

    # Same active-request check as the manual check endpoint, closing off reviewing a stale alert
    if trip_request.status != "active":
        raise HTTPException(
            status_code=400,
            detail=f"Request is {trip_request.status}, not active - this offer can no longer be reviewed or booked.",
        )

    current_observation = create_observation(trip_request, db)  # opening an offer runs a real fresh check

    now = now_for_request(trip_request)
    notification.reviewed_at = now
    if current_observation.status == "complete":
        # freezes this observation's price until each component's own hold expires
        notification.held_observation_id = current_observation.id
        set_component_holds(notification, now)
    else:
        # incomplete re-check invalidates any prior hold; there's no valid price left to honor
        notification.held_observation_id = None
        clear_component_holds(notification)

    db.commit()
    db.refresh(notification)

    # Built from the ORIGINAL alert observation, for "what was I alerted about", not the just-refreshed one
    notification_out = NotificationOut(
        id=notification.id,
        request_id=notification.request_id,
        observation_id=notification.observation_id,
        created_at=notification.created_at,
        reviewed_at=notification.reviewed_at,
        held_observation_id=notification.held_observation_id,
        held_until_flight=notification.held_until_flight,
        held_until_hotel=notification.held_until_hotel,
        held_until_cab=notification.held_until_cab,
        held_until=earliest_hold_deadline(notification),
        origin=trip_request.origin,
        destination=trip_request.destination,
        total_price=original_observation.total_price,
        quote_status=original_observation.status,
    )

    return NotificationReviewOut(
        notification=notification_out,
        original_observation=original_observation,
        current_observation=current_observation,
    )
