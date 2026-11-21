import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BookingAttempt, Notification
from app.schemas import BookingAttemptOut, BookingCreateIn
from app.sim_clock import sim_clock

router = APIRouter(prefix="/api/requests", tags=["booking"])
bookings_router = APIRouter(prefix="/api/bookings", tags=["booking"])


def _fake_supplier_ref(component: str) -> str:
    return f"SIM-{component.upper()}-{uuid.uuid4().hex[:8]}"


@router.post("/{request_id}/book", response_model=BookingAttemptOut)
def book(request_id: int, payload: BookingCreateIn, db: Session = Depends(get_db)):
    notification = (
        db.query(Notification)
        .filter(
            Notification.id == payload.notification_id,
            Notification.request_id == request_id,
        )
        .first()
    )
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found for this request")

    # Idempotency guard: calling this twice for the same notification (a
    # double-click, a retried request, two open tabs) must not create a
    # second booking - return the existing one instead. This is a baseline
    # correctness property, not a V2 failure scenario, so it belongs in V1.
    existing = (
        db.query(BookingAttempt)
        .filter(BookingAttempt.notification_id == notification.id)
        .first()
    )
    if existing is not None:
        return existing

    # Happy path only - V1 has no failure branch, every component "books"
    # successfully. The per-component status fields and "partial" aggregate
    # value exist now so V2's failure handling has somewhere to put a real
    # result without a schema change (docs/versions/V1_MODULES.md).
    booking = BookingAttempt(
        request_id=request_id,
        notification_id=notification.id,
        created_at=sim_clock.get_now(),
        accepted_total=payload.accepted_total,
        flight_status="confirmed",
        hotel_status="confirmed",
        cab_status="confirmed",
        aggregate_status="confirmed",
        supplier_ref_flight=_fake_supplier_ref("flight"),
        supplier_ref_hotel=_fake_supplier_ref("hotel"),
        supplier_ref_cab=_fake_supplier_ref("cab"),
    )
    db.add(booking)
    try:
        db.commit()
    except IntegrityError:
        # Two near-simultaneous requests both passed the check above before
        # either committed - the unique constraint on notification_id is what
        # actually makes this atomic. Whoever lost the race gets the winner's
        # row back, not an error.
        db.rollback()
        winner = (
            db.query(BookingAttempt)
            .filter(BookingAttempt.notification_id == notification.id)
            .first()
        )
        if winner is not None:
            return winner
        raise
    db.refresh(booking)
    return booking


@bookings_router.get("/{booking_id}", response_model=BookingAttemptOut)
def get_booking(booking_id: int, db: Session = Depends(get_db)):
    # Lets BookingResult.tsx survive a page refresh instead of only working
    # when the booking was just created in the same browser session.
    booking = db.query(BookingAttempt).filter(BookingAttempt.id == booking_id).first()
    if booking is None:
        raise HTTPException(status_code=404, detail="Booking not found")
    return booking
