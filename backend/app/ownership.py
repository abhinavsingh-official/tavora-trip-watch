"""Shared ownership-scoping helper (Sec. 03: requests/notifications/booking
actions must remain scoped to their owner). One implementation, used by
every router that needs it, rather than a copy-pasted filter per endpoint
that can drift - which is exactly how most of these endpoints ended up with
no ownership check at all until this pass found it.
"""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import BookingAttempt, Notification, TripRequest


def get_owned_request(request_id: int, user_id: int, db: Session) -> TripRequest:
    """
    A request that exists but belongs to someone else is a plain 404, not
    a 403 - doesn't confirm to a caller that the ID exists at all.
    """
    trip_request = (
        db.query(TripRequest)
        .filter(TripRequest.id == request_id, TripRequest.user_id == user_id)
        .first()
    )
    if trip_request is None:
        raise HTTPException(status_code=404, detail="Request not found")
    return trip_request


def get_owned_notification(notification_id: int, user_id: int, db: Session) -> Notification:
    notification = (
        db.query(Notification)
        .join(TripRequest, Notification.request_id == TripRequest.id)
        .filter(Notification.id == notification_id, TripRequest.user_id == user_id)
        .first()
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    return notification


def get_owned_booking(booking_id: int, user_id: int, db: Session) -> BookingAttempt:
    booking = (
        db.query(BookingAttempt)
        .join(TripRequest, BookingAttempt.request_id == TripRequest.id)
        .filter(BookingAttempt.id == booking_id, TripRequest.user_id == user_id)
        .first()
    )
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking
