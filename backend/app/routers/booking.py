import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import BookingAttempt, Notification
from app.schemas import BookingAttemptOut, BookingCreateIn
from app.sim_clock import sim_clock

router = APIRouter(prefix="/api/requests", tags=["booking"])


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
    db.commit()
    db.refresh(booking)
    return booking
