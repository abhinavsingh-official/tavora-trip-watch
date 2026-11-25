"""Operations view - surfaces anything stuck in a non-confirmed state plus a merged timeline per request."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BookingAttempt, Notification, PriceObservation, TripRequest
from app.ownership import get_owned_request
from app.schemas import BookingAttemptOut, TimelineEventOut

router = APIRouter(prefix="/api/ops", tags=["ops"])


@router.get("/partial-bookings", response_model=list[BookingAttemptOut])
def list_partial_bookings(user_id: int, db: Session = Depends(get_db)):
    return (
        db.query(BookingAttempt)
        .join(TripRequest, BookingAttempt.request_id == TripRequest.id)
        .filter(TripRequest.user_id == user_id, BookingAttempt.aggregate_status != "confirmed")
        .order_by(BookingAttempt.created_at.desc())
        .all()
    )


@router.get("/requests/{request_id}/timeline", response_model=list[TimelineEventOut])
def request_timeline(
    request_id: int,
    user_id: int,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
):
    """404s if not this user's request. Paginated: a long-lived request accumulates an unbounded
    number of observations/notifications/booking events the same way its own history does (§ see
    check.py's /observations) - each source query is capped before merging, then the merged,
    time-sorted result itself is paginated so `offset`/`limit` mean "most recent `limit`, `offset`
    further back" the way a reviewer would expect from a reverse-chronological feed."""
    get_owned_request(request_id, user_id, db)
    limit = max(1, min(limit, 500))
    offset = max(0, offset)
    # Each source capped generously (not by `limit` itself) so merging three sources doesn't starve
    # one of them of recent rows just because another had more events in the same window.
    per_source_cap = max(limit, 100)

    events: list[TimelineEventOut] = []

    observations = (
        db.query(PriceObservation)
        .filter(PriceObservation.request_id == request_id)
        .order_by(PriceObservation.observed_at.desc())
        .limit(per_source_cap)
    )
    for obs in observations:
        events.append(
            TimelineEventOut(
                type="observation",
                at=obs.observed_at,
                summary=f"Checked: {obs.status} - total ₹{obs.total_price if obs.total_price is not None else 'n/a'}",
            )
        )

    notifications = (
        db.query(Notification)
        .filter(Notification.request_id == request_id)
        .order_by(Notification.created_at.desc())
        .limit(per_source_cap)
    )
    for notif in notifications:
        events.append(
            TimelineEventOut(type="notification", at=notif.created_at, summary="Alert created")
        )
        if notif.reviewed_at is not None:
            events.append(
                TimelineEventOut(
                    type="notification", at=notif.reviewed_at, summary="Offer reviewed"
                )
            )

    bookings = (
        db.query(BookingAttempt)
        .filter(BookingAttempt.request_id == request_id)
        .order_by(BookingAttempt.created_at.desc())
        .limit(per_source_cap)
    )
    for booking in bookings:
        component_summary = (
            f"flight={booking.flight_status}, hotel={booking.hotel_status}, cab={booking.cab_status}"
        )
        events.append(
            TimelineEventOut(
                type="booking",
                at=booking.created_at,
                summary=f"Booking attempt started ({component_summary})",
            )
        )
        # a >1s gap between created_at and updated_at means something real happened later, not just row setup
        if (booking.updated_at - booking.created_at).total_seconds() > 1:
            events.append(
                TimelineEventOut(
                    type="booking",
                    at=booking.updated_at,
                    summary=f"Booking last changed: {booking.aggregate_status} ({component_summary})",
                )
            )

    events.sort(key=lambda e: e.at)

    # "Most recent `limit`, `offset` further back" - the end of the sorted list is the most recent
    total = len(events)
    end = total - offset
    if end <= 0:
        return []
    start = max(0, end - limit)
    return events[start:end]
