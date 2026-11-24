"""The operations view (Sec. 10) - a real required product screen, not
Scenario Lab tooling. Surfaces anything stuck in a non-confirmed state
(V2's partial-failure scenario produces exactly this) and a merged event
timeline per request, so a stuck booking isn't invisible.

Scoped per mock user, same as every other real screen - there's no separate
"operator" role anywhere in this app, so the operations view a user sees is
their own stuck bookings, not a global admin console.
"""

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
def request_timeline(request_id: int, user_id: int, db: Session = Depends(get_db)):
    """404s if not this user's request"""
    get_owned_request(request_id, user_id, db)

    events: list[TimelineEventOut] = []

    for obs in db.query(PriceObservation).filter(PriceObservation.request_id == request_id):
        events.append(
            TimelineEventOut(
                type="observation",
                at=obs.observed_at,
                summary=f"Checked: {obs.status} - total ₹{obs.total_price if obs.total_price is not None else 'n/a'}",
            )
        )

    for notif in db.query(Notification).filter(Notification.request_id == request_id):
        events.append(
            TimelineEventOut(type="notification", at=notif.created_at, summary="Alert created")
        )
        if notif.reviewed_at is not None:
            events.append(
                TimelineEventOut(
                    type="notification", at=notif.reviewed_at, summary="Offer reviewed"
                )
            )

    for booking in db.query(BookingAttempt).filter(BookingAttempt.request_id == request_id):
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
        """
        Audit finding #7: a booking that didn't resolve in one shot (a
        simulated restart, a timeout later reconciled, a compensating
        cancellation) used to show up as a single line with only its
        final status - the fact that anything happened in between was
        invisible. A >1s gap between created_at and updated_at means a
        real, separate event occurred later (not just the microseconds
        between inserting the row and setting its first component), so a
        second line is added for it.
        """
        if (booking.updated_at - booking.created_at).total_seconds() > 1:
            events.append(
                TimelineEventOut(
                    type="booking",
                    at=booking.updated_at,
                    summary=f"Booking last changed: {booking.aggregate_status} ({component_summary})",
                )
            )

    events.sort(key=lambda e: e.at)
    return events
